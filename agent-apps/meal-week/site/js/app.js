// Meal Week: reads the plan from config.js, draws the week and its grocery list, and keeps what the person
// does (the week on screen, the screen, the day, the items in the cart) in localStorage under "meal-week".
import { buildWeeks, keyOf, range } from "./plan.js";
import * as view from "./views.js";

const config = window.__APP_CONFIG__;
const STORE = "meal-week";
const weeks = buildWeeks(config);
const pantry = new Set((config.pantry || []).map(keyOf));
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (id) => document.getElementById(id);
const els = {
  board: $("board"), name: $("week-name"), meta: $("week-meta"), legend: $("legend"), range: $("picker-range"),
  prev: $("prev-week"), next: $("next-week"), viewport: $("week-viewport"), strip: $("days-strip"),
  list: $("list-panel"), shop: $("shop"), print: $("print-pages"), sheet: $("meal-sheet"), sheetBody: $("sheet-body"),
};

function load() {
  try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch { return {}; }
}
const saved = load();
const state = {
  week: weeks.some((w) => w.weekOf === saved.week) ? saved.week : config.weekOf,
  view: ["week", "list", "shop"].includes(saved.view) ? saved.view : "week",
  day: Number.isInteger(saved.day) ? saved.day : null,
  checks: saved.checks && typeof saved.checks === "object" ? saved.checks : {},
  seen: Boolean(saved.seen),
};
let quiet = false; // true while the first-look sequence runs, so nothing it does is kept
const save = () => {
  if (quiet) return;
  localStorage.setItem(STORE, JSON.stringify({ week: state.week, view: state.view, day: state.day, checks: state.checks, seen: true }));
};

const weekIndex = () => weeks.findIndex((w) => w.weekOf === state.week);
const current = () => weeks[weekIndex()];
const checksOf = (weekOf) => new Set(state.checks[weekOf] || []);
const phone = () => matchMedia("(max-width: 899px)").matches;

function startDay(week) {
  const today = week.days.findIndex((d) => d.isToday);
  return today >= 0 ? today : 0;
}

// Header, legend, list, shop, and the printed pages for the week on screen.
function renderChrome(week) {
  els.name.textContent = week.name;
  els.meta.innerHTML = `<span class="meta-range">${range(week.weekOf)} · </span>Cooking for ${config.people}`;
  els.legend.innerHTML = view.legend(week);
  els.range.textContent = range(week.weekOf);
  const i = weekIndex();
  els.prev.disabled = i <= 0;
  els.next.disabled = i >= weeks.length - 1;
  els.prev.hidden = els.next.hidden = weeks.length < 2;
  const checks = checksOf(week.weekOf);
  els.list.innerHTML = view.listPanel(week, config.people, checks);
  els.shop.innerHTML = view.shop(week, checks);
  els.print.innerHTML = view.printPages(week, config.slots, config.people, config.pantry || []);
  for (const a of document.querySelectorAll("[data-arc]")) a.style.setProperty("--arc", a.dataset.arc);
  els.strip.innerHTML = view.strip(week, state.day ?? 0);
}

function mountTrack(week) {
  const holder = document.createElement("div");
  holder.innerHTML = view.track(week, config.slots);
  const el = holder.firstElementChild;
  el.style.setProperty("--rows", config.slots.length);
  el.querySelectorAll("[data-arc]").forEach((a) => a.style.setProperty("--arc", a.dataset.arc));
  el.querySelectorAll(".day").forEach((d) => d.style.setProperty("--i", d.dataset.day));
  el.addEventListener("scroll", onTrackScroll, { passive: true });
  return el;
}

// A meal name that would run past two lines on a narrow tile steps down in size until it fits,
// and ingredient rows that do not fit are hidden from the end and counted in a "+N more" line.
function fitNames(root) {
  for (const n of root.querySelectorAll(".tile-name")) {
    n.style.removeProperty("--fit");
    n.classList.remove("is-long");
    for (let size = 14; n.scrollHeight > n.clientHeight + 1 && size >= 12; size -= 0.5) n.style.setProperty("--fit", `${size}px`);
    if (n.scrollHeight > n.clientHeight + 1) n.classList.add("is-long");
  }
  for (const box of root.querySelectorAll(".tile-ings")) {
    const rows = [...box.querySelectorAll(".ing")];
    for (const r of rows) r.hidden = false;
    box.querySelector(".ing-more")?.remove();
    const spills = () => box.lastElementChild.getBoundingClientRect().bottom > box.getBoundingClientRect().bottom + 0.5;
    if (!rows.length || !spills()) continue;
    const more = document.createElement("span");
    more.className = "ing-more";
    box.append(more);
    let hidden = 0;
    for (let i = rows.length - 1; i >= 0 && (hidden === 0 || spills()); i--) {
      rows[i].hidden = true;
      more.textContent = `+${++hidden} more`;
    }
  }
}

function showDay(track, day, smooth) {
  if (!phone()) return;
  track.scrollTo({ left: day * track.clientWidth, behavior: smooth && !reduced ? "smooth" : "instant" });
}

function setActiveDay(day) {
  state.day = day;
  for (const b of els.strip.querySelectorAll(".strip-day")) {
    const on = Number(b.dataset.goto) === day;
    b.classList.toggle("is-active", on);
    b.setAttribute("aria-selected", String(on));
  }
}

let scrollTimer = 0;
function onTrackScroll(e) {
  const t = e.currentTarget;
  const day = Math.round(t.scrollLeft / Math.max(1, t.clientWidth));
  if (day !== state.day) setActiveDay(day);
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(save, 250);
}

function render() {
  const week = current();
  if (state.day === null) state.day = startDay(week);
  renderChrome(week);
  els.viewport.replaceChildren(mountTrack(week));
  fitNames(els.viewport);
  setView(state.view, false);
  requestAnimationFrame(() => showDay(els.viewport.firstElementChild, state.day, false));
}

// The grid slides sideways: the old week leaves on one side while the new one comes in from the other.
let sliding = null;
function switchWeek(step) {
  const target = weekIndex() + step;
  if (target < 0 || target >= weeks.length) return;
  if (sliding) sliding.finish();
  const old = els.viewport.firstElementChild;
  state.week = weeks[target].weekOf;
  const week = current();
  renderChrome(week);
  const next = mountTrack(week);
  els.viewport.append(next);
  fitNames(next);
  showDay(next, state.day ?? 0, false);
  save();
  if (reduced || !old) { old?.remove(); return; }
  const opts = { duration: 420, easing: "cubic-bezier(0.77, 0, 0.175, 1)" };
  const outAnim = old.animate([{ transform: "translateX(0)", opacity: 1 }, { transform: `translateX(${-step * 104}%)`, opacity: 0.2 }], opts);
  const inAnim = next.animate([{ transform: `translateX(${step * 104}%)`, opacity: 0.2 }, { transform: "translateX(0)", opacity: 1 }], opts);
  sliding = { finish() { outAnim.finish(); inAnim.finish(); } };
  inAnim.finished.then(() => { old.remove(); sliding = null; }, () => {});
}

function setView(name, keep = true) {
  state.view = name;
  els.board.dataset.view = name;
  for (const t of document.querySelectorAll(".tab[data-view]")) t.setAttribute("aria-pressed", String(t.dataset.view === name));
  if (keep) save();
}

// The count swaps by rolling: the old number lifts away and the new one rises into its place.
function tick(countEl, value) {
  const old = countEl.querySelector(".num:not(.leaving)");
  if (!old || old.textContent === String(value)) return;
  countEl.setAttribute("aria-label", `${value} left`);
  const fresh = document.createElement("span");
  fresh.className = "num";
  fresh.textContent = value;
  if (reduced) { old.replaceWith(fresh); return; }
  countEl.querySelectorAll(".num.leaving").forEach((n) => n.remove());
  old.classList.add("leaving");
  countEl.append(fresh);
  const down = Number(value) < Number(old.textContent);
  const opts = { duration: 200, easing: "cubic-bezier(0.23, 1, 0.32, 1)" };
  old.animate([{ transform: "translateY(0)", opacity: 1 }, { transform: `translateY(${down ? -70 : 70}%)`, opacity: 0 }], opts).finished.then(() => old.remove(), () => {});
  fresh.animate([{ transform: `translateY(${down ? 70 : -70}%)`, opacity: 0 }, { transform: "translateY(0)", opacity: 1 }], opts);
}

function toggle(key, on) {
  const week = current();
  const checks = checksOf(week.weekOf);
  const next = on ?? !checks.has(key);
  if (next) checks.add(key); else checks.delete(key);
  state.checks[week.weekOf] = [...checks];
  for (const b of document.querySelectorAll(`.item[data-key="${CSS.escape(key)}"]`)) {
    b.classList.toggle("is-checked", next);
    b.setAttribute("aria-checked", String(next));
  }
  refreshCounts(week, checks);
  save();
}

function refreshCounts(week, checks) {
  let all = 0;
  for (const g of week.list.groups) {
    const left = g.items.filter((it) => !checks.has(it.key)).length;
    all += left;
    for (const c of document.querySelectorAll(`.count[data-count="${CSS.escape(g.aisle)}"]`)) tick(c, left);
  }
  for (const c of document.querySelectorAll('.count[data-count="all"]')) tick(c, all);
}

function clearCart() {
  const week = current();
  const checks = checksOf(week.weekOf);
  for (const key of checks) toggle(key, false);
}

function openSheet(dayIndex, slot) {
  els.sheetBody.innerHTML = view.sheet(current(), dayIndex, slot, pantry);
  els.sheetBody.querySelectorAll("[data-arc]").forEach((a) => a.style.setProperty("--arc", a.dataset.arc));
  els.sheet.showModal();
}

document.addEventListener("click", (e) => {
  const t = e.target.closest("button");
  if (!t) {
    if (e.target === els.sheet) els.sheet.close();
    return;
  }
  if (t.classList.contains("tile")) return openSheet(Number(t.dataset.day), t.dataset.slot);
  if (t.classList.contains("item")) return toggle(t.dataset.key);
  if (t.dataset.view) return setView(t.dataset.view);
  if (t.dataset.goto) { setActiveDay(Number(t.dataset.goto)); showDay(els.viewport.lastElementChild, state.day, true); return save(); }
  if (t.dataset.action === "close") return els.sheet.close();
  if (t.dataset.action === "clear") return clearCart();
  if (t === els.prev) return switchWeek(-1);
  if (t === els.next) return switchWeek(1);
  if (t.id === "print") return window.print();
});

document.addEventListener("keydown", (e) => {
  if (els.sheet.open || e.altKey || e.metaKey || e.ctrlKey) return;
  if (e.target.closest(".item, input, textarea")) return;
  if (e.key === "ArrowLeft" && !phone()) switchWeek(-1);
  if (e.key === "ArrowRight" && !phone()) switchWeek(1);
});

matchMedia("(max-width: 899px)").addEventListener("change", () => render());
let resizeTimer = 0;
addEventListener("resize", () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => fitNames(els.viewport), 150); });
document.fonts.ready.then(() => fitNames(els.viewport));
document.fonts.addEventListener("loadingdone", () => fitNames(els.viewport));

// The first look, on a first open only: the week slides to its neighbor and back, and on a wide screen three
// items go into the cart and come out again. The first touch, click, or key stops it, and it keeps nothing.
function firstLook() {
  if (reduced || state.seen || weeks.length < 1) return;
  quiet = true;
  const timers = [];
  const startWeek = state.week;
  const picked = [];
  const at = (ms, fn) => timers.push(setTimeout(fn, ms));
  const end = () => {
    timers.forEach(clearTimeout);
    removeEventListener("pointerdown", stop, true);
    removeEventListener("keydown", stop, true);
    for (const key of picked) toggle(key, false);
    if (state.week !== startWeek) {
      if (sliding) sliding.finish();
      state.week = startWeek;
      render();
    }
    quiet = false;
    state.seen = true;
  };
  const stop = () => end();
  addEventListener("pointerdown", stop, true);
  addEventListener("keydown", stop, true);
  const i = weekIndex();
  const step = i > 0 ? -1 : 1;
  if (weeks.length > 1) {
    at(2400, () => switchWeek(step));
    at(4400, () => switchWeek(-step));
  }
  const first = current().list.groups[0];
  if (first) {
    first.items.slice(0, 3).forEach((it, n) => at(6000 + n * 600, () => {
      if (phone() && state.view === "week") return;
      if (checksOf(state.week).has(it.key)) return;
      picked.push(it.key);
      toggle(it.key, true);
    }));
  }
  at(9400, end);
}

render();
setTimeout(() => document.body.classList.remove("opening"), reduced ? 0 : 1600);
firstLook();
