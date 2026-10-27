// Spend Map: reads data.js (monthly totals by category and merchant, written by run.py) and shows the Map, Months, and
// Categories screens. The screen, the month, the table's order, and the look are kept on this device.
import { createFlow } from "./flow.js";
import { renderMerchants } from "./merchants.js";
import { createOdometer } from "./odometer.js";
import { labelSegments, markMonth, renderChart, renderStrip } from "./months.js";
import { renderTable } from "./table.js";
import { money } from "./format.js";
import { load, save } from "./store.js";

const data = window.__SPEND_DATA__;
const app = document.querySelector(".app");
const $ = (slot) => document.querySelector(`[data-slot="${slot}"]`);
const SCREENS = ["map", "months", "categories"];
const SORTS = ["label", "spent", "share", "avg"];

const saved = load();
const firstOpen = !saved.month; // nothing kept on this device yet
const state = {
  screen: SCREENS.includes(saved.screen) ? saved.screen : "map",
  month: data.months.some((m) => m.key === saved.month) ? saved.month : data.months[data.months.length - 1].key,
  sort: saved.sort && SORTS.includes(saved.sort.key) ? { key: saved.sort.key, dir: saved.sort.dir === "asc" ? "asc" : "desc" } : { key: "spent", dir: "desc" },
  theme: saved.theme === "light" || saved.theme === "dark" ? saved.theme : null,
};
const persist = () => save(state);
const monthOf = (key) => data.months.find((m) => m.key === key);
const durationOf = (name, fallback) => {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v ? parseFloat(v) * (v.endsWith("ms") ? 1 : 1000) : fallback;
};

let pickedCat = null; // the category the narrow map's merchant list shows
const flow = createFlow($("flow"), data, { onPick: (cat) => { pickedCat = cat; renderSpots(); } });
const odometer = createOdometer($("total"), (cents) => money(data.currency, cents));
const tabs = $("month-tabs");
const strip = $("strip");
const table = { rowsEl: $("rows"), footEl: $("foot"), captionEl: $("table-caption"), headEl: document.querySelector(".cats thead") };

const first = data.months[0];
const last = data.months[data.months.length - 1];
$("range").textContent = first.key === last.key ? last.label
  : first.label.endsWith(last.label.slice(-4)) ? `${first.label.split(" ")[0]} to ${last.label}` : `${first.label} to ${last.label}`;

for (const m of data.months) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "month-tab";
  b.setAttribute("role", "tab");
  b.dataset.month = m.key;
  b.textContent = m.short;
  b.title = m.label;
  b.addEventListener("click", () => pickMonth(m.key));
  tabs.appendChild(b);
}

function heroFor(month, { first: isFirst }) {
  const income = month.income.reduce((s, x) => s + x.cents, 0);
  const diff = income - month.spent;
  $("month-title").textContent = month.label;
  odometer.set(month.spent, { duration: isFirst ? durationOf("--motion-draw", 1200) : durationOf("--motion-slow", 400) });
  $("income").textContent = money(data.currency, income);
  $("kept-word").textContent = diff >= 0 ? "Saved" : "From savings";
  $("kept").textContent = money(data.currency, Math.abs(diff));
  const named = new Map(data.categories.map((c) => [c.id, c.label]));
  const top = [...month.categories].sort((a, b) => b.cents - a.cents)[0];
  $("top").textContent = top ? `${named.get(top.id) || "Other"}, ${Math.round((top.cents / Math.max(1, month.spent)) * 100)}%` : "";
  for (const b of tabs.children) {
    const on = b.dataset.month === month.key;
    b.setAttribute("aria-selected", String(on));
    b.tabIndex = on ? 0 : -1;
  }
}

function pickMonth(key, { screen, keep = true } = {}) {
  if (screen) showScreen(screen);
  if (key === state.month && !screen) return;
  state.month = key;
  if (keep) persist();
  const month = monthOf(key);
  heroFor(month, { first: false });
  if (state.screen === "map") { flow.show(month); renderSpots(); }
  markMonth(strip, key);
  markMonth($("chart"), key);
  renderTable(table, data, month, state.sort);
}

let mapShown = false;
function showScreen(screen) {
  state.screen = screen;
  persist();
  app.dataset.screen = screen;
  for (const panel of document.querySelectorAll("[data-screen-panel]")) panel.hidden = panel.dataset.screenPanel !== screen;
  for (const b of document.querySelectorAll("[data-go]")) {
    if (b.dataset.go === screen) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  }
  if (screen === "map") {
    const month = monthOf(state.month);
    if (!mapShown) { mapShown = true; flow.show(month); } else { flow.relayout(month); if (flow.month !== month.key) flow.show(month); }
    renderSpots();
  }
  if (screen === "months") requestAnimationFrame(() => labelSegments($("chart")));
}

// On a narrow map the merchants leave the map for a list under it: the picked category's, else the month's largest.
function renderSpots() {
  const list = $("merchants");
  list.hidden = !flow.compact;
  if (!flow.compact) return;
  const month = monthOf(state.month);
  if (!month.categories.some((c) => c.id === pickedCat)) pickedCat = [...month.categories].sort((a, b) => b.cents - a.cents)[0]?.id ?? null;
  renderMerchants(list, data, month, pickedCat);
  flow.markPicked(pickedCat);
}

for (const b of document.querySelectorAll("[data-go]")) b.addEventListener("click", () => showScreen(b.dataset.go));

for (const b of table.headEl.querySelectorAll("[data-sort]")) {
  b.addEventListener("click", () => {
    const key = b.dataset.sort;
    state.sort = state.sort.key === key ? { key, dir: state.sort.dir === "asc" ? "desc" : "asc" } : { key, dir: key === "label" ? "asc" : "desc" };
    persist();
    renderTable(table, data, monthOf(state.month), state.sort);
  });
}

// The look: theme.css sets one for the device; the switch picks the other and is remembered.
const themeButton = document.querySelector("[data-action='theme']");
const lookNow = () => getComputedStyle(document.documentElement).getPropertyValue("--look").trim();
function syncThemeButton() {
  const dark = lookNow() === "vault";
  themeButton.setAttribute("aria-label", dark ? "Switch to light" : "Switch to dark");
  themeButton.classList.toggle("is-dark", dark);
}
function repaint() {
  syncThemeButton();
  flow.recolor();
  renderStrip(strip, data, (key) => pickMonth(key));
  renderChart($("chart"), $("legend"), data, (key) => pickMonth(key, { screen: "map" }));
  markMonth(strip, state.month);
  markMonth($("chart"), state.month);
  renderTable(table, data, monthOf(state.month), state.sort);
  if (mapShown) renderSpots();
}
themeButton.addEventListener("click", () => {
  state.theme = lookNow() === "vault" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", state.theme);
  persist();
  repaint();
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", repaint);

document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") flow.clearFocus();
  if (e.target.closest && e.target.closest("input, textarea, select")) return;
  if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
  const i = data.months.findIndex((m) => m.key === state.month);
  const next = data.months[i + (e.key === "ArrowRight" ? 1 : -1)];
  if (next) {
    pickMonth(next.key);
    if (e.target.closest && e.target.closest(".month-tabs")) tabs.querySelector(`[data-month="${next.key}"]`).focus();
  }
});

let resizeFrame = 0;
new ResizeObserver(() => {
  cancelAnimationFrame(resizeFrame);
  resizeFrame = requestAnimationFrame(() => {
    if (state.screen === "map" && mapShown) { flow.relayout(monthOf(state.month)); renderSpots(); }
    if (state.screen === "months") labelSegments($("chart"));
  });
}).observe($("flow"));

async function start() {
  await Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 400))]);
  syncThemeButton();
  repaint();
  heroFor(monthOf(state.month), { first: true });
  showScreen(state.screen);
  app.classList.add("is-ready");
  showOnce();
}

// Once the map has drawn, the widest ribbon lights with its amount for a moment, the way hovering one does, unless
// the person has already reached for the page. On the first open on a device, the map then shows the costliest other
// month for a moment and comes back, so the months strip is seen to move it; that visit to the other month is not kept.
function showOnce() {
  let reached = false;
  const reach = () => { reached = true; };
  for (const type of ["pointerdown", "keydown", "wheel"]) addEventListener(type, reach, { once: true, passive: true });
  $("flow").addEventListener("pointerover", reach, { once: true, passive: true });
  const draw = durationOf("--motion-draw", 1200);
  if (state.screen !== "map" || draw <= 0) return;
  setTimeout(() => {
    if (reached || state.screen !== "map") return;
    flow.focusWidest();
    setTimeout(() => {
      if (reached) return;
      flow.clearFocus();
      const home = state.month;
      const away = data.months.filter((m) => m.key !== home).sort((a, b) => b.spent - a.spent)[0];
      if (!firstOpen || !away) return;
      setTimeout(() => {
        if (reached || state.screen !== "map") return;
        pickMonth(away.key, { keep: false });
        setTimeout(() => { if (!reached && state.month === away.key) pickMonth(home, { keep: false }); }, 1800);
      }, 400);
    }, 2000);
  }, draw + 2400);
}
start();
