// Year in Pixels: the year grid, the radial picker, the sheets, and what the person colored, wired together.
import { todayIso, yearOf, addDays, daysIn, iso, longDate, parse } from "./dates.js";
import { loadDays, saveDays, clean, picker as pickerState, exportFile } from "./store.js";
import { exampleYear } from "./example.js";
import { createGrid } from "./grid.js";
import { createPicker } from "./picker.js";
import { createDaySheet, createStatsSheet, createSettingsSheet } from "./sheets.js";
import { yearStats } from "./stats.js";

const config = window.__APP_CONFIG__;
const $ = (id) => document.getElementById(id);
const root = document.documentElement;
const wide = window.matchMedia("screen and (min-width: 900px) and (orientation: landscape)");
const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");

config.moods.forEach((m, i) => root.style.setProperty(`--mood-${i + 1}`, m.color));
root.dataset.paper = config.paper;
document.title = `${config.name}, ${config.year} in pixels`;

const today = todayIso();
const thisYear = yearOf(today);
let days = loadDays();
if (days === null) {
  days = config.example ? exampleYear(config.year, config.year < thisYear ? `${config.year + 1}-01-01` : today) : {};
}
const firstYear = Math.min(config.year, thisYear, ...Object.keys(days).map(yearOf)) - 1;
const lastYear = Math.max(config.year, thisYear);
let year = config.year;
let focusDay = null;

const grid = createGrid($("grid"), $("ribbon"), config.moods);

function persist() {
  saveDays(days);
}

// The legend is the only chrome: five swatches, each with its count for the year in view.
function legend() {
  const s = yearStats(days, year, config.weekStart);
  $("legend").replaceChildren(
    ...config.moods.map((m, i) => {
      const key = document.createElement("span");
      key.className = "key";
      const sw = document.createElement("span");
      sw.className = "key-swatch";
      sw.style.setProperty("--key-color", `var(--mood-${i + 1})`);
      const label = document.createElement("span");
      label.className = "key-label";
      label.textContent = m.label;
      const count = document.createElement("span");
      count.className = "key-count";
      count.textContent = String(s.counts[i + 1]);
      key.append(sw, label, count);
      return key;
    }),
  );
  const total = year === thisYear ? dayOfYear(today) : year < thisYear ? daysInYear(year) : 0;
  const best = s.best ? ` ${s.best.name} was the best month.` : "";
  $("facts").textContent = total
    ? `${s.total} of ${total} days colored${year === thisYear ? " so far" : ""}.${best}`
    : `${year} has not started yet. Its days fill in as they come.`;
}

const daysInYear = (y) => (daysIn(y, 1) === 29 ? 366 : 365);
const dayOfYear = (day) => Math.round((parse(day) - new Date(yearOf(day), 0, 1)) / 86400000) + 1;

function header() {
  $("who").textContent = config.name;
  $("year").textContent = String(year);
  $("prev").disabled = year <= firstYear;
  $("next").disabled = year >= lastYear;
  $("prev").setAttribute("aria-label", `Show ${year - 1}`);
  $("next").setAttribute("aria-label", `Show ${year + 1}`);
}

function startDay() {
  if (year === thisYear) return today;
  return year < thisYear ? `${year}-12-31` : `${year}-01-01`;
}

function setFocusable(day) {
  const cells = grid.cells();
  if (focusDay && cells.get(focusDay)) cells.get(focusDay).tabIndex = -1;
  focusDay = day;
  cells.get(day).tabIndex = 0;
}

function show() {
  picker.close();
  header();
  grid.render(year, days, today);
  setFocusable(startDay());
  legend();
  return grid.stagger();
}

function update(day) {
  const cell = grid.cells().get(day);
  if (cell) grid.paint(cell, days[day]);
  grid.ribbon(year, days);
  legend();
}

function setMood(day, level) {
  const prev = days[day];
  days[day] = prev && prev.note ? { mood: level, note: prev.note } : { mood: level };
  persist();
  update(day);
  const cell = grid.cells().get(day);
  picker.close();
  pickerState.set("closed");
  if (cell) {
    grid.pop(cell);
    setFocusable(day);
    if (cell.contains(document.activeElement) || $("ring").contains(document.activeElement)) cell.focus({ preventScroll: true });
  }
}

const picker = createPicker($("picker"), $("ring"), config.moods, {
  onPick: (day, level) => setMood(day, level),
  onNote: (day) => {
    picker.close();
    pickerState.set("closed");
    daySheet.open(day, days[day]);
  },
  onDismiss: () => pickerState.set("closed"),
});

const daySheet = createDaySheet(config.moods, {
  onSave(day, level, note) {
    const text = note.replace(/\s+/g, " ").trim().slice(0, 120);
    days[day] = text ? { mood: level, note: text } : { mood: level };
    persist();
    update(day);
    const cell = grid.cells().get(day);
    if (cell) {
      grid.pop(cell);
      cell.focus({ preventScroll: true });
    }
  },
  onClear(day) {
    delete days[day];
    persist();
    update(day);
  },
});

const statsSheet = createStatsSheet(config.moods);

const settingsSheet = createSettingsSheet(config, {
  onExport() {
    const url = URL.createObjectURL(exportFile(days, config));
    const a = document.createElement("a");
    a.href = url;
    a.download = `year-in-pixels-${config.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "export"}.json`;
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
  async onImport(file) {
    let incoming;
    try {
      incoming = clean(JSON.parse(await file.text()));
    } catch {
      return "That file is not an export from Year in Pixels.";
    }
    const n = Object.keys(incoming).length;
    if (!n) return "That file has no colored days in it.";
    Object.assign(days, incoming);
    persist();
    show();
    return `Added ${n === 1 ? "one day" : `${n} days`} from ${file.name}.`;
  },
  onClear(y) {
    for (const day of Object.keys(days)) if (yearOf(day) === y) delete days[day];
    persist();
    show();
  },
});

function openPicker(cell, opts) {
  if (cell.dataset.future !== undefined) return;
  hideTip();
  setFocusable(cell.dataset.day);
  picker.open(cell, days[cell.dataset.day], opts);
  pickerState.set(cell.dataset.day);
}

$("grid").addEventListener("click", (e) => {
  const cell = e.target.closest(".cell");
  if (!cell) return;
  if (picker.day() === cell.dataset.day) {
    picker.close();
    pickerState.set("closed");
    return;
  }
  openPicker(cell, { focus: e.detail === 0 });
});

// Arrow keys move one day along the column and one month across, in whichever way the grid is drawn.
$("grid").addEventListener("keydown", (e) => {
  const cell = e.target.closest(".cell");
  if (!cell) return;
  const day = cell.dataset.day;
  if (/^[1-5]$/.test(e.key) && cell.dataset.future === undefined) {
    e.preventDefault();
    setMood(day, Number(e.key));
    return;
  }
  const m = Number(day.slice(5, 7)) - 1;
  const d = Number(day.slice(8, 10));
  const across = (dm) => {
    const nm = Math.min(11, Math.max(0, m + dm));
    return iso(year, nm, Math.min(d, daysIn(year, nm)));
  };
  const along = (dd) => {
    const next = addDays(day, dd);
    return yearOf(next) === year ? next : day;
  };
  const moves = wide.matches
    ? { ArrowRight: () => along(1), ArrowLeft: () => along(-1), ArrowDown: () => across(1), ArrowUp: () => across(-1) }
    : { ArrowDown: () => along(1), ArrowUp: () => along(-1), ArrowRight: () => across(1), ArrowLeft: () => across(-1) };
  const extra = { Home: () => iso(year, m, 1), End: () => iso(year, m, daysIn(year, m)) };
  const move = moves[e.key] || extra[e.key];
  if (!move) return;
  e.preventDefault();
  const target = grid.cells().get(move());
  picker.close();
  setFocusable(target.dataset.day);
  target.focus();
});

const tip = $("tip");
function hideTip() {
  tip.hidden = true;
}
$("grid").addEventListener("pointerover", (e) => {
  const cell = e.target.closest(".cell");
  if (!cell || e.pointerType !== "mouse" || !finePointer.matches || picker.day()) return;
  const entry = days[cell.dataset.day];
  const date = document.createElement("div");
  date.className = "tip-date";
  date.textContent = longDate(cell.dataset.day);
  const mood = document.createElement("div");
  mood.className = "tip-mood";
  mood.textContent = entry ? config.moods[entry.mood - 1].label : cell.dataset.future !== undefined ? "Still to come" : "No mood yet";
  tip.style.setProperty("--tip-color", entry ? `var(--mood-${entry.mood})` : "var(--color-empty)");
  const parts = [date, mood];
  if (entry && entry.note) {
    const note = document.createElement("div");
    note.className = "tip-note";
    note.textContent = entry.note;
    parts.push(note);
  }
  tip.replaceChildren(...parts);
  tip.hidden = false;
  const r = cell.getBoundingClientRect();
  const t = tip.getBoundingClientRect();
  const x = Math.min(Math.max(r.left + r.width / 2 - t.width / 2, 8), window.innerWidth - t.width - 8);
  const above = r.top - t.height - 10;
  const y = above > 8 ? above : r.bottom + 10;
  tip.style.setProperty("--tx", `${Math.round(x)}px`);
  tip.style.setProperty("--ty", `${Math.round(y)}px`);
});
$("grid").addEventListener("pointerleave", hideTip);
$("grid").addEventListener("pointerout", (e) => {
  if (!e.relatedTarget || !e.relatedTarget.closest || !e.relatedTarget.closest(".cell")) hideTip();
});

$("prev").addEventListener("click", () => {
  year -= 1;
  show();
});
$("next").addEventListener("click", () => {
  year += 1;
  show();
});
$("legend").addEventListener("click", () => statsSheet.open(days, year, config.weekStart, today));
$("open-stats").addEventListener("click", () => statsSheet.open(days, year, config.weekStart, today));
$("open-settings").addEventListener("click", () => settingsSheet.open(year));

window.addEventListener("resize", () => {
  hideTip();
  picker.place();
});
window.addEventListener("beforeprint", () => {
  picker.close();
  hideTip();
});

// After the opening sweep the picker rises on today when today has no color yet, or on the day it was open on.
show().then(() => {
  const saved = pickerState.get();
  if (saved === "closed") return;
  const day = saved && yearOf(saved) === year ? saved : today;
  const cell = grid.cells().get(day);
  if (!cell || cell.dataset.future !== undefined) return;
  if (day === today && days[today] && !saved) return;
  openPicker(cell);
});
