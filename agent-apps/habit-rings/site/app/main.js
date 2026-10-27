// Habit Rings: reads the habits from config.js and the days from this browser, then wires Today, the Year, and Settings.
import { addDays, daysBetween, dayKey, hourWords, longDate, partOfDay, shortDate } from "./dates.js";
import { createChips } from "./chips.js";
import { createDial, DIAL_MAX } from "./dial.js";
import { createOdometer } from "./odometer.js";
import { createSheet } from "./sheet.js";
import { allClosed, countOf, goal, loadData, loadPrefs, saveData, savePrefs, setCount, streakOf } from "./store.js";
import { createYear } from "./year.js";

const config = window.__APP_CONFIG__ || {};
const habits = (Array.isArray(config.habits) ? config.habits : []).slice(0, 8).filter((h) => h && h.id);
const THEMES = ["auto", "ink", "paper", "neon"];

const motion = matchMedia("(prefers-reduced-motion: reduce)");
const reduced = () => motion.matches;
const wide = matchMedia("(min-width: 700px)");

let today = new Date();
let day = today;
let data = loadData({ ...config, habits }, today);
const prefs = loadPrefs();
let weekStart = prefs.weekStart === "sun" || prefs.weekStart === "mon" ? prefs.weekStart : config.weekStart === "sun" ? "sun" : "mon";
let theme = THEMES.includes(prefs.theme) ? prefs.theme : THEMES.includes(config.theme) ? config.theme : "auto";

const $ = (selector) => document.querySelector(selector);
const greeting = $(".greeting");
const dateLine = $(".date-line");
const unit = $(".streak-unit");
const line = $(".streak-line");
const dayLabel = $(".day-label");
const prev = $(".day-prev");
const next = $(".day-next");
const status = $(".status");

const dial = createDial({
  root: $(".dial"),
  habits,
  reduced,
  onTap: (i) => tap(i, 1),
  onSwipe: (direction) => move(direction),
});
const chips = createChips({
  root: $(".chips"),
  habits,
  reduced,
  onTap: (i) => tap(i, 1),
  onLess: (i) => tap(i, -1),
});
const odometer = createOdometer($(".odometer"), reduced);
const year = createYear({ list: $(".habit-rows"), habits, tip: $(".tip"), reduced, desktop: () => wide.matches });

function counts(key) {
  return habits.map((habit) => countOf(data, key, habit));
}

function renderHello() {
  const name = typeof config.name === "string" ? config.name.trim() : "";
  greeting.textContent = `Good ${partOfDay(today)}${name ? `, ${name}` : ""}`;
  dateLine.textContent = longDate(today);
}

function renderDay({ draw = false } = {}) {
  const key = dayKey(day);
  const now = counts(key);
  dial.set(now.slice(0, DIAL_MAX).map((n, i) => n / goal(habits[i])), { draw });
  const closed = habits.filter((habit, i) => now[i] >= goal(habit)).length;
  dial.setCenter(closed, habits.length);
  chips.set(now);
  const back = daysBetween(day, today);
  dayLabel.textContent = back === 0 ? "Today" : back === 1 ? "Yesterday" : shortDate(day);
  dayLabel.classList.toggle("is-past", back > 0);
  next.disabled = back <= 0;
  prev.disabled = back >= 364;
}

function renderStreak() {
  const { count, todayClosed } = streakOf(data, habits, today);
  odometer.set(count);
  unit.textContent = count === 1 ? "day with every ring closed" : "days in a row with every ring closed";
  const key = dayKey(today);
  const open = habits.filter((habit) => countOf(data, key, habit) < goal(habit)).length;
  const hour = Number.isInteger(config.nudgeHour) ? config.nudgeHour : 20;
  const late = !todayClosed && today.getHours() >= hour && open > 0;
  line.classList.toggle("is-nudge", late);
  const rings = open === 1 ? "ring is" : "rings are";
  if (habits.length === 0) line.textContent = "Add habits to your inputs to get your rings.";
  else if (late) line.textContent = `It's past ${hourWords(hour)} and ${open === 1 ? "one" : open} ${rings} still open.`;
  else if (todayClosed) line.textContent = "Every ring is closed today.";
  else if (count === 0) line.textContent = open === habits.length ? "Close every ring today to start a streak." : `Close ${open === 1 ? "the last one" : `the last ${open}`} today to start a streak.`;
  else line.textContent = `Close ${open === 1 ? "one more" : `${open} more`} today to make it ${count + 1}.`;
  status.hidden = !data.sample;
}

function save() {
  saveData(data);
}

/** A tap on a habit for the day in view: a plain habit closes or opens, a countable one moves by `delta`. */
function tap(index, delta) {
  const habit = habits[index];
  if (!habit) return;
  const key = dayKey(day);
  const was = countOf(data, key, habit);
  const wasAll = allClosed(data, key, habits);
  let to;
  if (habit.target) to = was + delta;
  else to = delta < 0 ? 0 : was >= 1 ? 0 : 1;
  if (habit.target && to > habit.target) {
    chips.pop(index);
    return;
  }
  const now = setCount(data, key, habit, to, habits);
  if (now === was) return;
  save();
  renderDay();
  year.paint(data, today);
  renderStreak();
  if (now >= goal(habit) && was < goal(habit)) {
    dial.snap(index);
    chips.pop(index);
    if (!wasAll && allClosed(data, key, habits)) setTimeout(() => dial.bloom("var(--color-accent)", 1.2), 260);
  } else if (habit.target && delta > 0) {
    chips.pop(index);
  }
}

function move(direction) {
  const to = addDays(day, direction);
  const back = daysBetween(to, today);
  if (back < 0 || back > 364) return;
  day = to;
  renderDay();
  dial.slide(direction);
}

function applyTheme(name) {
  theme = name;
  let link = document.getElementById("theme-pick");
  if (!link) {
    link = document.createElement("link");
    link.rel = "stylesheet";
    link.id = "theme-pick";
    document.getElementById("theme").after(link);
  }
  link.href = `./themes/${name}.css`;
  savePrefs({ ...loadPrefs(), theme: name });
}

createSheet({
  dialog: $(".sheet"),
  opener: $(".settings-open"),
  getState: () => ({ weekStart, theme, data, habits }),
  onWeekStart: (value) => {
    weekStart = value;
    savePrefs({ ...loadPrefs(), weekStart: value });
    year.build(data, today, weekStart);
  },
  onTheme: applyTheme,
  onImport: (loaded) => {
    data = loaded;
    save();
    renderAll();
  },
  onClearSample: () => {
    data = { days: {}, counts: {}, sample: false };
    save();
    renderAll();
  },
});

prev.addEventListener("click", () => move(-1));
next.addEventListener("click", () => move(1));

document.addEventListener("keydown", (event) => {
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
  if ($(".sheet").open || event.target.closest?.("input, textarea, select")) return;
  const digit = /^Digit([1-8])$/.exec(event.code);
  if (digit) {
    event.preventDefault();
    tap(Number(digit[1]) - 1, event.shiftKey ? -1 : 1);
  } else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    if (event.target.closest?.(".map-scroll")) return;
    event.preventDefault();
    move(event.key === "ArrowLeft" ? -1 : 1);
  }
});

function renderAll({ opening = false } = {}) {
  renderHello();
  renderDay({ draw: opening });
  renderStreak();
  year.build(data, today, weekStart, { opening });
}

// A page left open keeps time: the nudge turns on at its hour, and a new day starts at midnight.
setInterval(() => {
  const now = new Date();
  if (dayKey(now) !== dayKey(today)) {
    const following = dayKey(day) === dayKey(today);
    today = now;
    if (following) day = now;
    renderAll();
  } else {
    today = now;
    renderHello();
    renderStreak();
  }
}, 60000);

$(".today").classList.toggle("has-many", habits.length > 6);
renderAll({ opening: true });
document.documentElement.classList.add("is-ready");
