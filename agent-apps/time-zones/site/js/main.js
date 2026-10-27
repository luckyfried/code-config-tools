// Time Zones: one strip per person, colored by the hour where they are, all laid on the person's own day, with a line
// to drag to a time. The column under the line glows when every row is inside its working hours.
import {
  HOUR, wall, offsetMin, midnight, isoDate, addDays, localMinute, clock, hourMark, relWords, inWindow,
} from "./zones.js";
import { readPalette, skyAt } from "./sky.js";
import { createDial } from "./dial.js";
import { load, save } from "./store.js";

const cfg = window.__APP_CONFIG__;
const FORMAT = cfg.hourFormat === 12 ? 12 : 24;
const HOME = cfg.home.zone;
const reduce = matchMedia("(prefers-reduced-motion: reduce)");
const phoneQuery = matchMedia("(max-width: 720px)");
const darkQuery = matchMedia("(prefers-color-scheme: dark)");
const MIN = 60000;

const $ = (id) => document.getElementById(id);
const root = document.documentElement;
const app = $("app"), board = $("board"), scroller = $("scroller"), lanesEl = $("lanes"), axisTrack = $("axis-track");
const line = $("line"), knob = $("knob"), knobTime = $("knob-time"), column = $("column");
const statusText = $("status-text"), details = $("details"), copyBtn = $("copy"), copyLabel = $("copy-label");
const dateInput = $("date"), dateLabel = $("date-label"), toNow = $("to-now"), themeBtn = $("theme");

const rows = [
  {
    you: true, name: "You", city: cfg.home.label, zone: HOME,
    workStart: cfg.home.workStart ?? 9, workEnd: cfg.home.workEnd ?? 17,
  },
  ...cfg.people.map((p) => ({ ...p })),
];

const saved = load();
const todayIso = () => isoDate(HOME, Date.now());
if (!saved.date || saved.date < todayIso()) { delete saved.date; delete saved.t; }

const state = { date: saved.date || todayIso(), t: 0, dayStart: 0, phone: phoneQuery.matches };
const geo = { trackLeft: 0, hourW: 1, top: 0, lanesTop: 0 };
let palette = readPalette();

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
};
const pct = (n) => `${n}%`;
const clampT = (t) => Math.min(24 - 1 / 60, Math.max(0, t));
// t is the hour on the home clock (0 to 24), so 15 means 15:00 at home even on a day the clocks change.
function instAt(t) {
  const base = state.dayStart + t * HOUR;
  return base + (offsetMin(HOME, state.dayStart) - offsetMin(HOME, base)) * MIN;
}
const exactNow = () => {
  const w = wall(HOME, Date.now());
  return w.h + w.mi / 60 + w.s / 3600;
};
// On a phone the day snaps to whole hours under the line, so "now" there is the start of the current hour.
const nowT = () => (state.phone ? Math.floor(exactNow()) : exactNow());
const isToday = () => state.date === todayIso();

function listWords(names) {
  if (names.length === 1) return names[0];
  if (names.length === 2) return `${names[0]} and ${names[1]}`;
  return `${names.slice(0, -1).join(", ")}, and ${names[names.length - 1]}`;
}

const dayWords = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
function isoWords(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return dayWords.format(Date.UTC(y, m - 1, d));
}

// ---------- the rows ----------

for (const [i, row] of rows.entries()) {
  const lane = el("div", `lane${row.you ? " is-you" : ""}`);
  lane.style.setProperty("--i", String(i));
  lane.style.setProperty("--person", row.color || `var(--people-${i % 6})`);
  const who = el("div", "who");
  row.who = who;
  row.dial = createDial(row.zone);
  const text = el("div", "who-text");
  const top = el("div", "who-top");
  top.append(el("span", "who-name", row.name));
  row.timeEl = el("span", "who-time");
  row.dayEl = el("span", "who-day");
  const time = el("span", "who-when");
  time.append(row.dayEl, row.timeEl);
  top.append(time);
  const where = el("div", "who-where");
  row.offsetEl = el("span", "who-offset");
  where.append(el("span", "who-city", row.city), row.offsetEl);
  row.noteEl = el("div", "who-note");
  text.append(top, where, row.noteEl);
  who.append(row.dial.svg, text);

  const track = el("div", "track");
  const strip = el("div", "strip");
  row.skyEl = el("div", "sky");
  row.marksEl = el("div", "marks");
  strip.append(row.skyEl, row.marksEl);
  row.workEl = el("div", "work");
  track.append(strip, row.workEl);
  lane.append(who, track);
  lane.dataset.row = String(i);
  row.lane = lane;
  lanesEl.append(lane);
}

// ---------- one day ----------

function relAt(row, ms) {
  return offsetMin(row.zone, ms) - offsetMin(HOME, ms);
}

function nextChange(row) {
  const mid0 = state.dayStart + 12 * HOUR;
  const first = row.you ? offsetMin(HOME, mid0) : relAt(row, mid0);
  for (let d = 1; d <= 14; d++) {
    const iso = addDays(state.date, d);
    const mid = midnight(HOME, iso) + 12 * HOUR;
    const value = row.you ? offsetMin(HOME, mid) : relAt(row, mid);
    if (value !== first) {
      if (row.you) return `Clocks go ${value < first ? "back" : "forward"} ${isoWords(iso)}`;
      return `${relWords(value)} from ${isoWords(iso)}`;
    }
  }
  return "";
}

function paintRow(row) {
  const stops = [];
  const marks = [];
  const work = [];
  let runStart = -1;
  let offset = 0;
  for (let k = -12; k <= 108; k++) {
    const inst = instAt(k / 4);
    if (k % 4 === 0 || k === -12) offset = offsetMin(row.zone, inst);
    const minute = ((((inst / MIN + offset) % 1440) + 1440) % 1440);
    const sky = skyAt(palette, minute);
    stops.push(`${sky.css} ${((k + 12) / 120 * 100).toFixed(2)}%`);
    if (k < 0 || k > 96) continue;
    if (k < 96 && minute % 180 === 0) {
      const label = minute === 0 ? wall(row.zone, inst).wd : hourMark(minute / 60, FORMAT);
      marks.push([k / 96 * 100, label, sky.light, minute === 0]);
    }
    const on = k < 96 && inWindow(minute, row.workStart, row.workEnd);
    if (on && runStart < 0) runStart = k;
    if (!on && runStart >= 0) { work.push([runStart, k]); runStart = -1; }
  }
  row.skyEl.style.setProperty("--sky", `linear-gradient(90deg, ${stops.join(", ")})`);
  row.markEls = marks.map(([x, label, light, isMidnight]) => {
    const m = el("span", `mark${light ? " on-light" : ""}${isMidnight ? " is-midnight" : ""}`, label);
    m.style.setProperty("--x", pct(x));
    m.hour = (x / 100) * 24;
    return m;
  });
  row.marksEl.replaceChildren(...row.markEls);
  row.workEl.replaceChildren(...work.map(([a, b]) => {
    const seg = el("i");
    seg.style.setProperty("--x", pct(a / 96 * 100));
    seg.style.setProperty("--w", pct((b - a) / 96 * 100));
    return seg;
  }));
}

function renderDay({ flash = false } = {}) {
  state.dayStart = midnight(HOME, state.date);
  const mid = state.dayStart + 12 * HOUR;
  for (const row of rows) {
    const rel = row.you ? 0 : relAt(row, mid);
    const before = row.rel;
    row.rel = rel;
    paintRow(row);
    row.offsetEl.textContent = row.you ? "your time" : relWords(rel);
    row.noteEl.textContent = nextChange(row);
    if (flash && before !== undefined && before !== rel) flashRow(row, (before - rel) / 60);
  }
  renderAxis();
  const today = todayIso();
  dateInput.value = state.date;
  const rel = state.date === today ? "Today" : state.date === addDays(today, 1) ? "Tomorrow" : state.date === addDays(today, -1) ? "Yesterday" : "";
  dateLabel.replaceChildren(el("span", "date-main", isoWords(state.date)), ...(rel ? [el("span", "date-rel", rel)] : []));
}

function flashRow(row, hours) {
  if (!reduce.matches) {
    row.skyEl.animate(
      [{ transform: `translateX(${(-hours / 30) * 100}%)` }, { transform: "translateX(0)" }],
      { duration: 900, easing: "cubic-bezier(0.77, 0, 0.175, 1)" },
    );
  }
  row.lane.classList.remove("is-flash");
  void row.lane.offsetWidth;
  row.lane.classList.add("is-flash");
  clearTimeout(row.flashTimer);
  row.flashTimer = setTimeout(() => row.lane.classList.remove("is-flash"), 1800);
}

function goodAt(t) {
  const inst = instAt(Math.round(t * 60) / 60);
  return rows.every((r) => inWindow(localMinute(r.zone, inst), r.workStart, r.workEnd)
    && inWindow(localMinute(r.zone, inst + 59 * MIN), r.workStart, r.workEnd));
}

function renderAxis() {
  const parts = [];
  for (let h = 0; h <= 24; h++) {
    const tick = el("span", `tick${h % 3 === 0 ? " is-third" : ""}`);
    tick.style.setProperty("--x", pct(h / 24 * 100));
    parts.push(tick);
    if (h < 24) {
      const label = el("span", `hour${h % 3 === 0 ? " is-third" : ""}`, hourMark(h, FORMAT));
      label.style.setProperty("--x", pct(h / 24 * 100));
      const snap = el("span", "snap");
      snap.style.setProperty("--x", pct(h / 24 * 100));
      parts.push(label, snap);
    }
  }
  const dot = el("span", "now-dot");
  dot.hidden = !isToday();
  dot.style.setProperty("--x", pct(Math.min(100, Math.max(0, exactNow() / 24 * 100))));
  parts.push(dot);
  axisTrack.replaceChildren(...parts);
}

// ---------- the line ----------

function measure() {
  state.phone = phoneQuery.matches;
  const b = board.getBoundingClientRect();
  const first = rows[0].lane.querySelector(".track").getBoundingClientRect();
  const last = rows[rows.length - 1].lane.querySelector(".strip").getBoundingClientRect();
  const axis = axisTrack.getBoundingClientRect();
  geo.trackLeft = first.left - b.left + scroller.scrollLeft;
  geo.hourW = first.width / 24;
  geo.width = b.width;
  geo.top = axis.top - b.top;
  geo.lanesTop = first.top - b.top;
  // The column, its glow ring, and the line all end at the bottom edge of the last strip.
  const bottom = last.bottom - b.top;
  line.style.setProperty("--top", `${geo.top}px`);
  line.style.setProperty("--h", `${bottom - 4 - geo.top}px`);
  for (const row of rows) {
    const r = row.who.getBoundingClientRect();
    row.pill = [r.left - b.left, r.right - b.left];
  }
  column.style.setProperty("--top", `${geo.lanesTop - 6}px`);
  column.style.setProperty("--h", `${bottom - geo.lanesTop + 6}px`);
}

function syncScroll() {
  if (state.phone) scroller.scrollLeft = state.t * geo.hourW;
}

let lastGood = null;
let lastText = "";
function update() {
  const t = state.t;
  const x = geo.trackLeft + t * geo.hourW - scroller.scrollLeft;
  line.style.setProperty("--x", `${x}px`);
  column.style.setProperty("--x", `${x}px`);
  column.style.setProperty("--w", `${Math.min(1, 24 - t) * geo.hourW}px`);

  const inst = instAt(Math.round(t * 60) / 60);
  const homeWall = wall(HOME, inst);
  const outside = [];
  const seen = new Set();
  const entries = [];
  for (const row of rows) {
    for (const m of row.markEls) {
      // On a phone every label stays in front of the column; on a desktop a label steps aside for the line's own hour.
      let hide = !state.phone && m.hour > t - 0.45 && m.hour < t + 1.2;
      if (state.phone && row.pill) {
        // On a phone the name pill floats over the strip's left end; a label it would cover, or one the screen's edge would cut, is hidden whole.
        const x = geo.trackLeft + m.hour * geo.hourW - scroller.scrollLeft;
        hide ||= (x + 34 > row.pill[0] && x < row.pill[1] + 4) || x + 26 > geo.width;
      }
      m.classList.toggle("is-near", hide);
    }
    const w = wall(row.zone, inst);
    const time = clock(w.h, w.mi, FORMAT);
    row.timeEl.textContent = time;
    const otherDay = w.wd !== homeWall.wd;
    row.dayEl.textContent = otherDay ? w.wd : "";
    const end = localMinute(row.zone, inst + 59 * MIN);
    const working = inWindow(w.h * 60 + w.mi, row.workStart, row.workEnd) && inWindow(end, row.workStart, row.workEnd);
    row.lane.classList.toggle("is-off", !working);
    if (!working) outside.push(row.you ? "you" : row.name);
    const key = `${row.city}|${row.zone}`;
    if (!seen.has(key)) {
      seen.add(key);
      entries.push({ when: row.you || otherDay ? `${w.wd} ${time}` : time, city: row.city, you: row.you });
    }
  }
  const good = outside.length === 0;
  if (good !== lastGood) {
    lastGood = good;
    column.classList.toggle("is-good", good);
    app.classList.toggle("is-good", good);
  }
  statusText.textContent = good
    ? "Good for everyone"
    : outside.length === rows.length ? "Outside work hours for everyone" : `Outside work hours for ${listWords(outside)}`;

  const text = entries.map((e) => `${e.when} ${e.city}`).join(" / ");
  if (text !== lastText) {
    lastText = text;
    const parts = [];
    entries.forEach((e, i) => {
      if (i) parts.push(el("span", "d-sep", " / "));
      const entry = el("span", `d-entry${e.you ? " is-you" : ""}`);
      entry.append(el("span", "d-time", e.when), " ", el("span", "d-city", e.city));
      parts.push(entry);
    });
    details.replaceChildren(...parts);
  }

  const homeTime = clock(homeWall.h, homeWall.mi, FORMAT);
  knobTime.textContent = homeTime;
  knob.setAttribute("aria-valuenow", String(homeWall.h * 60 + homeWall.mi));
  knob.setAttribute("aria-valuetext", `${homeTime} in ${cfg.home.label}, ${statusText.textContent.toLowerCase()}`);
  toNow.hidden = isToday() && Math.abs(t - nowT()) < 1 / 60;
}

// ---------- motion of the line ----------

let raf = 0;
function stopMotion() { cancelAnimationFrame(raf); raf = 0; scroller.classList.remove("no-snap"); }

function setT(t) {
  state.t = clampT(t);
  if (state.phone) scroller.scrollLeft = state.t * geo.hourW;
  update();
}

/** Glides the line to `target` over `ms`, easing in and out; the phone's day scrolls under it the same way. */
function glide(target, ms, done) {
  stopMotion();
  target = clampT(target);
  if (reduce.matches || ms <= 0) { setT(target); done?.(); return; }
  const from = state.t;
  const t0 = performance.now();
  scroller.classList.add("no-snap");
  const step = (now) => {
    const p = Math.min(1, (now - t0) / ms);
    const e = p < 0.5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2;
    setT(from + (target - from) * e);
    if (p < 1) { raf = requestAnimationFrame(step); return; }
    raf = 0;
    scroller.classList.remove("no-snap");
    done?.();
  };
  raf = requestAnimationFrame(step);
}

/** Settles the line on `target` with a small spring, the magnetic ease of letting go near an hour. */
function settle(target) {
  stopMotion();
  target = clampT(target);
  if (reduce.matches) { setT(target); return; }
  let v = 0;
  let last = performance.now();
  const step = (now) => {
    const dt = Math.min(0.032, (now - last) / 1000);
    last = now;
    v += (260 * (target - state.t) - 24 * v) * dt;
    const next = state.t + v * dt;
    if (Math.abs(target - next) < 0.0008 && Math.abs(v) < 0.01) { setT(target); raf = 0; return; }
    state.t = next;
    update();
    raf = requestAnimationFrame(step);
  };
  raf = requestAnimationFrame(step);
}

function remember() {
  saved.date = state.date;
  saved.t = Math.round(state.t * 60) / 60;
  save(saved);
}

// Desktop: drag anywhere on the strips. Near an hour the line is pulled toward it; on release it settles there.
let dragging = false;
function pointerT(e) {
  const b = board.getBoundingClientRect();
  return (e.clientX - b.left - geo.trackLeft) / geo.hourW;
}
board.addEventListener("pointerdown", (e) => {
  if (state.phone || e.button !== 0) return;
  const raw = pointerT(e);
  if (raw < -0.4 || raw > 24.4) return;
  dragging = true;
  board.setPointerCapture(e.pointerId);
  board.classList.add("is-dragging");
  stopMotion();
  knob.focus({ preventScroll: true });
  dragTo(raw);
});
function dragTo(raw) {
  const n = Math.round(raw);
  const d = raw - n;
  const pull = Math.abs(d) < 0.22 ? (Math.abs(d) / 0.22) ** 1.6 : 1;
  state.t = clampT(n + d * pull);
  update();
}
board.addEventListener("pointermove", (e) => { if (dragging) dragTo(pointerT(e)); });
const release = (e) => {
  if (!dragging) return;
  dragging = false;
  board.classList.remove("is-dragging");
  const target = Math.min(23, Math.max(0, Math.round(pointerT(e))));
  settle(target);
  saved.date = state.date; saved.t = target; save(saved);
};
board.addEventListener("pointerup", release);
board.addEventListener("pointercancel", release);

// Phone: the day scrolls under a fixed line, snapping to hours.
let scrollTimer = 0;
scroller.addEventListener("scroll", () => {
  // A scroll that lands where the page put the day is the page's own; anything else is the person's finger.
  if (!state.phone || Math.abs(scroller.scrollLeft - state.t * geo.hourW) < 1) return;
  stopMotion();
  state.t = clampT(scroller.scrollLeft / geo.hourW);
  update();
  if (!touched) return;
  clearTimeout(scrollTimer);
  scrollTimer = setTimeout(remember, 250);
}, { passive: true });
// Only a scroll the person made is remembered; the browser's own settling onto an hour is not a pick.
let touched = false;
for (const type of ["pointerdown", "touchstart", "wheel", "keydown"]) {
  scroller.addEventListener(type, () => { touched = true; }, { passive: true });
}

// Keyboard: arrows move by an hour, with Shift by fifteen minutes.
document.addEventListener("keydown", (e) => {
  if (e.target === dateInput || e.altKey || e.ctrlKey || e.metaKey) return;
  const dir = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1 }[e.key];
  if (!dir) return;
  if (e.target !== knob && e.target.closest?.("button") && (e.key === "ArrowUp" || e.key === "ArrowDown")) return;
  e.preventDefault();
  const step = e.shiftKey ? 0.25 : 1;
  const from = raf ? targetOf(state.t) : state.t;
  const next = dir > 0 ? Math.floor(from / step + 1e-6) * step + step : Math.ceil(from / step - 1e-6) * step - step;
  glide(Math.min(24 - step, Math.max(0, next)), 160, remember);
});
const targetOf = (t) => t;

// ---------- controls ----------

function changeDate(iso, keep = true) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso) || iso === state.date) return;
  state.date = iso;
  renderDay({ flash: true });
  measure();
  update();
  if (keep) remember();
}

/** The first day within two weeks on which any row's clock moves against today, or "". */
function comingChange() {
  const mid0 = state.dayStart + 12 * HOUR;
  const today = rows.map((r) => offsetMin(r.zone, mid0));
  for (let d = 1; d <= 14; d++) {
    const iso = addDays(state.date, d);
    const mid = midnight(HOME, iso) + 12 * HOUR;
    if (rows.some((r, i) => offsetMin(r.zone, mid) !== today[i])) return iso;
  }
  return "";
}
dateInput.addEventListener("change", () => changeDate(dateInput.value));
$("prev-day").addEventListener("click", () => changeDate(addDays(state.date, -1)));
$("next-day").addEventListener("click", () => changeDate(addDays(state.date, 1)));
$("date-label").parentElement.addEventListener("click", () => { try { dateInput.showPicker(); } catch {} });

toNow.addEventListener("click", () => {
  const today = todayIso();
  if (state.date !== today) { state.date = today; renderDay({ flash: true }); }
  delete saved.date; delete saved.t; save(saved);
  glide(nowT(), 500);
});

function effectiveDark() {
  if (root.dataset.theme) return root.dataset.theme === "dark";
  return cfg.theme === "night" || (cfg.theme === "auto" && darkQuery.matches);
}
function paintTheme() {
  const dark = effectiveDark();
  themeBtn.classList.toggle("is-dark", dark);
  themeBtn.setAttribute("aria-label", dark ? "Switch to the day look" : "Switch to the night look");
  palette = readPalette();
  for (const row of rows) paintRow(row);
  tick();
}
themeBtn.addEventListener("click", () => {
  root.dataset.theme = effectiveDark() ? "light" : "dark";
  saved.theme = root.dataset.theme;
  save(saved);
  paintTheme();
});
darkQuery.addEventListener("change", () => { if (!root.dataset.theme) paintTheme(); });

let copyTimer = 0;
copyBtn.addEventListener("click", async () => {
  const text = lastText;
  let label = "Copied";
  try {
    if (!window.isSecureContext || !navigator.clipboard) throw new Error("no clipboard");
    await navigator.clipboard.writeText(text);
  } catch {
    const range = document.createRange();
    range.selectNodeContents(details);
    const sel = getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    label = /Mac|iPhone|iPad/.test(navigator.platform) ? "Press ⌘C to copy" : "Press Ctrl+C to copy";
  }
  copyLabel.textContent = label;
  copyBtn.classList.add("is-done");
  clearTimeout(copyTimer);
  copyTimer = setTimeout(() => { copyLabel.textContent = "Copy times"; copyBtn.classList.remove("is-done"); }, 1800);
});

// ---------- clocks ----------

function tick() {
  const now = Date.now();
  for (const row of rows) row.dial.draw(now, palette);
}
function tickLoop() {
  tick();
  setTimeout(tickLoop, 1000 - (Date.now() % 1000) + 5);
}
setInterval(() => {
  if (!isToday()) return;
  const dot = axisTrack.querySelector(".now-dot");
  if (dot) dot.style.setProperty("--x", pct(Math.min(100, Math.max(0, exactNow() / 24 * 100))));
  update();
}, 30000);

// ---------- start ----------

renderDay();
paintTheme();
requestAnimationFrame(() => app.classList.add("is-ready"));
tickLoop();
measure();
// The rows rise into place once; the line and the column are measured again where they land.
$("lanes").addEventListener("animationend", (e) => { if (e.target === rows[rows.length - 1].lane) { measure(); update(); } });

const start = saved.t !== undefined ? saved.t : isToday() ? nowT() : Math.max(0, Math.min(23, rows[0].workStart));
state.t = clampT(start);
syncScroll();
update();

new ResizeObserver(() => {
  const wasPhone = state.phone;
  measure();
  if (state.phone !== wasPhone || state.phone) syncScroll();
  update();
}).observe(board);

// The first visit shows what the page is for: the line glides from now to the next hour that suits everyone.
if (!saved.toured && saved.t === undefined && isToday()) {
  saved.toured = true;
  save(saved);
  const from = state.t;
  const timers = [];
  const later = (ms, fn) => timers.push(setTimeout(fn, ms));
  if (!goodAt(from)) {
    let target = -1;
    for (let h = Math.ceil(from); h < 24; h++) if (goodAt(h)) { target = h; break; }
    if (target >= 0) later(250, () => glide(target, 1100));
  }
  // When a clock change is near, the tour steps to that day so the rows that move flash their new offset, then returns.
  const today = state.date;
  const change = comingChange();
  if (change) {
    later(3200, () => changeDate(change, false));
    later(6800, () => changeDate(today, false));
  }
  // Anything the person does ends the tour where it is.
  const stop = () => { timers.forEach(clearTimeout); for (const t of ["pointerdown", "keydown", "wheel", "touchstart"]) removeEventListener(t, stop, true); };
  for (const t of ["pointerdown", "keydown", "wheel", "touchstart"]) addEventListener(t, stop, { capture: true, passive: true });
}
