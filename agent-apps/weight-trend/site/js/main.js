// Weight Trend: reads the run's config, keeps the weigh-ins in this browser, and draws Today, Chart, and Settings.

import { createStore, toKg, fromKg } from "./store.js";
import { withTrend, projection, weekDelta, todayDay, isoOf, HOLD_KG_PER_WEEK } from "./trend.js";
import { createChart } from "./chart.js";
import { createStepper } from "./stepper.js";
import * as fmt from "./format.js";

const raw = window.__APP_CONFIG__ || {};
const config = {
  name: typeof raw.name === "string" ? raw.name.trim() : "",
  units: raw.units === "lb" ? "lb" : "kg",
  goal: typeof raw.goal === "number" && raw.goal > 0 ? raw.goal : raw.units === "lb" ? 165 : 75,
  smoothing: typeof raw.smoothing === "number" && raw.smoothing > 0 && raw.smoothing < 1 ? raw.smoothing : 0.1,
  showProjection: raw.showProjection !== false,
  sample: raw.sample === true,
};

const store = createStore(config);
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

let today = todayDay();
let state = compute();

function compute() {
  const points = withTrend(store.entries, config.smoothing);
  const goalKg = store.goalKg;
  return {
    points,
    goalKg,
    units: store.units,
    proj: projection(points, goalKg),
    week: weekDelta(points),
    showProjection: config.showProjection,
    today,
  };
}

const todayEntry = () => store.entries.find((e) => e.date === isoOf(today));
const lastPoint = () => state.points[state.points.length - 1];

// The header.
function greet() {
  const h = new Date().getHours();
  const part = h < 5 ? "Good evening" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
  $("[data-greeting]").textContent = config.name ? `${part}, ${config.name}` : part;
  $("[data-today-date]").textContent = fmt.day(today, "long");
  document.title = config.name ? `Weight Trend for ${config.name}` : "Weight Trend";
}

// The delta chip: the trend's change over seven days, with an arrow that turns to match it.
const chip = $("[data-chip]");
const chipArrow = chip.querySelector(".chip-arrow");
function renderChip(first) {
  const { week, units, goalKg } = state;
  const last = lastPoint();
  chip.hidden = week === null;
  if (week === null) return;
  const holding = Math.abs(week) < HOLD_KG_PER_WEEK;
  const toward = Math.sign(week) === Math.sign(goalKg - last.trend);
  chip.dataset.dir = holding ? "holding" : toward ? "toward" : "away";
  $("[data-chip-text]").textContent = holding ? "Holding" : `${fmt.change(week, units)} this week`;
  const angle = holding ? 0 : Math.max(-60, Math.min(60, -week * 60));
  if (first && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
    chipArrow.style.setProperty("--angle", "0deg");
    setTimeout(() => chipArrow.style.setProperty("--angle", `${angle.toFixed(1)}deg`), 650);
  } else {
    chipArrow.style.setProperty("--angle", `${angle.toFixed(1)}deg`);
  }
  chip.setAttribute("aria-label", holding ? "Holding steady this week" : `${fmt.change(week, units)} over the last seven days`);
}

function renderSummary() {
  const { units, goalKg, proj, showProjection, points } = state;
  const last = lastPoint();
  $("[data-trend-value]").textContent = last ? fmt.weight(last.trend, units) : "–";
  const goalLabel = $("[data-goal-label]");
  const goalValue = $("[data-goal-date]");
  const toGo = last ? fmt.weight(Math.abs(goalKg - last.trend), units) : null;
  goalLabel.textContent = `Goal ${fmt.weight(goalKg, units)}`;
  if (!last) goalValue.textContent = "First weigh-in";
  else if (proj.state === "reached") goalValue.textContent = "Reached";
  else if (proj.state === "toward" && showProjection) goalValue.textContent = fmt.day(Math.round(proj.day));
  else goalValue.textContent = `${toGo} to go`;

  $("[data-stat-trend]").textContent = last ? fmt.weight(last.trend, units) : "–";
  const week = state.week;
  $("[data-stat-week]").textContent =
    week === null ? "Two weigh-ins start the weekly change." : Math.abs(week) < HOLD_KG_PER_WEEK ? "Holding over the last seven days" : `${fmt.change(week, units)} over the last seven days`;
  $("[data-stat-togo]").textContent = !last ? fmt.weight(goalKg, units) : proj.state === "reached" ? "Reached" : toGo;
  const whenBox = $("[data-stat-when-box]");
  whenBox.hidden = !showProjection;
  const when = $("[data-stat-when]");
  const whenSub = $("[data-stat-when-sub]");
  whenSub.textContent = "";
  if (proj.state === "toward") {
    when.textContent = fmt.day(Math.round(proj.day));
    whenSub.textContent = fmt.inDays(Math.round(proj.day) - today);
  } else {
    when.textContent = { empty: "–", reached: "Reached", holding: "Holding", away: "Moving away" }[proj.state];
  }
  $("[data-stat-since]").textContent = points.length > 1 ? fmt.change(last.trend - points[0].trend, units) : "–";
  $("[data-stat-count]").textContent = String(points.length);
  renderRecent();
  for (const el of $$("[data-unit]")) el.textContent = units;
}

function aboveBelow(p, units) {
  const off = fromKg(p.value - p.trend, units);
  return Math.abs(off) < 0.05 ? "On the line" : `${fmt.plain(Math.abs(off))} ${off > 0 ? "above" : "below"}`;
}

function renderRecent() {
  const list = $("[data-recent]");
  const { points, units } = state;
  list.replaceChildren();
  for (const p of points.slice(-8).reverse()) {
    const li = document.createElement("li");
    const d = document.createElement("span");
    d.className = "recent-day";
    d.textContent = p.day === today ? "Today" : fmt.day(p.day, "row");
    const v = document.createElement("span");
    v.className = "recent-value num";
    v.textContent = fmt.weight(p.value, units);
    const off = document.createElement("span");
    off.className = "recent-diff num";
    off.textContent = aboveBelow(p, units);
    li.append(d, v, off);
    list.append(li);
  }
  // Only whole rows show: a row the card cannot fit is left out.
  const bottom = list.parentElement.getBoundingClientRect().bottom;
  for (const li of [...list.children]) if (li.getBoundingClientRect().bottom > bottom) li.remove();
}
addEventListener("resize", () => renderRecent());

// Today: the dial and the log button.
const logButton = $("[data-log]");
const noteInput = $("[data-note]");
const stepper = createStepper($(".entry"), {
  onChange: () => renderLogButton(),
  onConfirm: () => logToday(),
});

function renderLogButton(justLogged = false) {
  const entry = todayEntry();
  const same = entry && Math.abs(fromKg(entry.value, state.units) - stepper.value) < 0.05 && (entry.note || "") === noteInput.value.trim();
  const label = $("[data-log-text]");
  if (entry && same) {
    logButton.dataset.state = "logged";
    label.textContent = justLogged ? "Logged" : "Logged today";
  } else {
    delete logButton.dataset.state;
    label.textContent = entry ? "Update today" : "Log weigh-in";
  }
}

function startValue() {
  const entry = todayEntry();
  if (entry) return fromKg(entry.value, state.units);
  const last = lastPoint();
  if (last) return fromKg(last.trend, state.units);
  return fromKg(state.goalKg, state.units);
}

function logToday() {
  const kg = toKg(stepper.value, state.units);
  store.put(isoOf(today), kg, noteInput.value);
  state = compute();
  renderAll({ ease: true });
  renderLogButton(true);
}

$("[data-entry-form]").addEventListener("submit", (e) => {
  e.preventDefault();
  logToday();
});
noteInput.addEventListener("input", () => renderLogButton());

// The two charts.
const todayChart = createChart($('[data-chart="today"]'), { span: 90 });
const rangeChart = createChart($('[data-chart="range"]'), { span: 90 });

// Chart: the range buttons and the list of weigh-ins.
const RANGE_TITLES = { 90: "Last 90 days", 365: "Last year", all: "Every weigh-in" };
for (const button of $$("[data-range]")) {
  button.addEventListener("click", () => {
    const span = button.dataset.range === "all" ? "all" : Number(button.dataset.range);
    for (const b of $$("[data-range]")) b.setAttribute("aria-pressed", String(b === button));
    $("[data-range-title]").textContent = RANGE_TITLES[span];
    rangeChart.setSpan(span);
  });
}

function renderList() {
  const list = $("[data-entries]");
  const { points, units } = state;
  list.replaceChildren();
  if (!points.length) {
    const li = document.createElement("li");
    li.className = "entries-empty";
    li.textContent = "Your weigh-ins show here, newest first.";
    list.append(li);
    return;
  }
  for (let i = points.length - 1; i >= 0; i -= 1) {
    const p = points[i];
    const li = document.createElement("li");
    li.className = "entry-item";
    const when = document.createElement("div");
    when.className = "entry-when";
    const dayEl = document.createElement("p");
    dayEl.className = "entry-day";
    dayEl.textContent = p.day === today ? "Today" : fmt.day(p.day, p.day > today - 300 ? "row" : "year");
    when.append(dayEl);
    if (p.note) {
      const note = document.createElement("p");
      note.className = "entry-note";
      note.textContent = p.note;
      when.append(note);
    }
    const value = document.createElement("p");
    value.className = "entry-value num";
    value.textContent = fmt.weight(p.value, units);
    const diff = document.createElement("p");
    diff.className = "entry-diff num";
    diff.textContent = aboveBelow(p, units);
    const del = document.createElement("button");
    del.type = "button";
    del.className = "entry-delete";
    del.setAttribute("aria-label", `Delete the weigh-in of ${fmt.day(p.day, "long")}`);
    del.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17"/></svg>';
    del.addEventListener("click", () => {
      if (!del.hasAttribute("data-armed")) {
        del.setAttribute("data-armed", "");
        del.textContent = "Delete";
        setTimeout(() => {
          if (del.isConnected && del.hasAttribute("data-armed")) {
            del.removeAttribute("data-armed");
            del.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17"/></svg>';
          }
        }, 3000);
        return;
      }
      store.remove(p.date);
      state = compute();
      renderAll({ ease: true });
      if (p.date === isoOf(today)) stepper.set(startValue(), { duration: 200 });
    });
    li.append(when, value, diff, del);
    list.append(li);
  }
}

// Settings.
function renderSettings() {
  for (const b of $$("[data-units]")) b.setAttribute("aria-pressed", String(b.dataset.units === state.units));
  const goalInput = $("[data-goal-input]");
  if (document.activeElement !== goalInput) goalInput.value = fmt.plain(fromKg(state.goalKg, state.units));
}

for (const button of $$("[data-units]")) {
  button.addEventListener("click", () => {
    if (button.dataset.units === state.units) return;
    const kg = toKg(stepper.value, state.units);
    store.setUnits(button.dataset.units);
    state = compute();
    stepper.set(fromKg(kg, state.units), { duration: 0 });
    renderAll({});
  });
}

$("[data-goal-form]").addEventListener("submit", (e) => {
  e.preventDefault();
  const status = $("[data-goal-status]");
  const v = Number($("[data-goal-input]").value.replace(",", "."));
  if (!Number.isFinite(v) || v < 1 || v > 999) {
    status.dataset.tone = "error";
    status.textContent = `Enter a goal in ${state.units === "lb" ? "pounds" : "kilograms"}, like ${state.units === "lb" ? "165" : "75"}.`;
    return;
  }
  store.setGoalKg(toKg(v, state.units));
  state = compute();
  renderAll({ ease: true });
  delete status.dataset.tone;
  status.textContent = `Goal saved: ${fmt.weight(state.goalKg, state.units)}.`;
});

$("[data-export]").addEventListener("click", () => {
  const blob = new Blob([store.exportJson()], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `weight-trend-${isoOf(today)}.json`;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  const status = $("[data-data-status]");
  delete status.dataset.tone;
  status.textContent = `Exported ${store.entries.length} weigh-ins.`;
});

$("[data-import]").addEventListener("change", async (e) => {
  const file = e.target.files && e.target.files[0];
  const status = $("[data-data-status]");
  if (!file) return;
  try {
    const n = store.importJson(await file.text());
    state = compute();
    renderAll({ ease: true });
    stepper.set(startValue(), { duration: 200 });
    delete status.dataset.tone;
    status.textContent = `Imported ${n} weigh-ins.`;
  } catch (err) {
    status.dataset.tone = "error";
    status.textContent = err.message;
  }
  e.target.value = "";
});

function aboutText() {
  const s = config.smoothing;
  const words = { 0.5: "half", 0.25: "a quarter", 0.2: "a fifth", 0.1: "a tenth", 0.05: "a twentieth" }[s] || `${Math.round(s * 100)} percent`;
  $("[data-about]").textContent = `Each weigh-in moves the trend ${words} of the way toward the scale, so water and salt wash out and only the real change stays. The goal date follows the trend's last seven days.`;
}

// Tabs.
let screen = "today";
const drawnOnce = new Set(["today"]);
for (const tab of $$("[data-tab]")) {
  tab.addEventListener("click", () => show(tab.dataset.tab));
}
function show(name) {
  screen = name;
  for (const s of $$("[data-screen]")) s.hidden = s.dataset.screen !== name;
  for (const t of $$("[data-tab]")) {
    if (t.dataset.tab === name) t.setAttribute("aria-current", "page");
    else t.removeAttribute("aria-current");
  }
  if (name === "chart") rangeChart.draw(state, { intro: !drawnOnce.has("chart") });
  if (name === "today") todayChart.draw(state, {});
  drawnOnce.add(name);
}

function renderAll({ intro = false, ease = false }) {
  renderChip(intro);
  renderSummary();
  renderList();
  renderSettings();
  if (screen === "today") todayChart.draw(state, { intro, ease });
  if (screen === "chart") rangeChart.draw(state, { ease });
}

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState !== "visible" || todayDay() === today) return;
  today = todayDay();
  state = compute();
  greet();
  renderAll({});
  stepper.set(startValue(), { duration: 0 });
  noteInput.value = (todayEntry() && todayEntry().note) || "";
});

greet();
aboutText();
noteInput.value = (todayEntry() && todayEntry().note) || "";
await document.fonts.ready;
stepper.start(startValue());
renderAll({ intro: true });
renderLogButton();
