// The person's days, kept in this browser under habit-rings:v1 as { days: { "2026-10-21": ["water", "run"] } },
// with the partial counts of countable habits beside them, and the page's own choices under habit-rings:prefs.
import { addDays, dayKey } from "./dates.js";

const DATA_KEY = "habit-rings:v1";
const PREFS_KEY = "habit-rings:prefs";
const DAY = /^\d{4}-\d{2}-\d{2}$/;

function read(key) {
  try {
    const text = localStorage.getItem(key);
    return text === null ? null : JSON.parse(text);
  } catch {
    return null;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

/** The days in `value` when it has the stored shape, else null. */
export function cleanData(value) {
  if (!value || typeof value !== "object" || !value.days || typeof value.days !== "object" || Array.isArray(value.days)) return null;
  const days = {};
  for (const [key, ids] of Object.entries(value.days)) {
    if (!DAY.test(key) || !Array.isArray(ids)) return null;
    const kept = ids.filter((id) => typeof id === "string");
    if (kept.length) days[key] = [...new Set(kept)];
  }
  const counts = {};
  if (value.counts && typeof value.counts === "object") {
    for (const [key, row] of Object.entries(value.counts)) {
      if (!DAY.test(key) || !row || typeof row !== "object") continue;
      const kept = {};
      for (const [id, n] of Object.entries(row)) if (Number.isInteger(n) && n > 0) kept[id] = n;
      if (Object.keys(kept).length) counts[key] = kept;
    }
  }
  return { days, counts, sample: value.sample === true };
}

export function loadData(config, today) {
  const stored = cleanData(read(DATA_KEY));
  if (stored) return stored;
  if (config.sample) return { ...sampleYear(config.habits, today), sample: true };
  return { days: {}, counts: {}, sample: false };
}

export const saveData = (data) => write(DATA_KEY, data);

export const loadPrefs = () => {
  const prefs = read(PREFS_KEY);
  return prefs && typeof prefs === "object" ? prefs : {};
};

export const savePrefs = (prefs) => write(PREFS_KEY, prefs);

// What a day holds for one habit.
export const isDone = (data, key, habit) => (data.days[key] || []).includes(habit.id);

export function countOf(data, key, habit) {
  if (!habit.target) return isDone(data, key, habit) ? 1 : 0;
  const n = data.counts[key]?.[habit.id];
  if (Number.isInteger(n)) return Math.min(n, habit.target);
  return isDone(data, key, habit) ? habit.target : 0;
}

export const goal = (habit) => habit.target || 1;

export const progress = (data, key, habit) => countOf(data, key, habit) / goal(habit);

function setDone(data, key, habit, done, habits) {
  const now = new Set(data.days[key] || []);
  if (done) now.add(habit.id);
  else now.delete(habit.id);
  const order = habits.map((h) => h.id);
  const ids = [...now].sort((a, b) => order.indexOf(a) - order.indexOf(b));
  if (ids.length) data.days[key] = ids;
  else delete data.days[key];
}

/** Sets a habit's count for a day: a countable habit closes at its target, a plain one at 1. */
export function setCount(data, key, habit, n, habits) {
  const target = goal(habit);
  const count = Math.max(0, Math.min(target, n));
  if (habit.target) {
    const row = { ...(data.counts[key] || {}) };
    if (count > 0 && count < target) row[habit.id] = count;
    else delete row[habit.id];
    if (Object.keys(row).length) data.counts[key] = row;
    else delete data.counts[key];
  }
  setDone(data, key, habit, count >= target, habits);
  return count;
}

export const allClosed = (data, key, habits) => {
  const ids = data.days[key];
  return Boolean(ids) && habits.every((h) => ids.includes(h.id));
};

/** Days in a row with every ring closed: through today once today is closed, else through yesterday. */
export function streakOf(data, habits, today) {
  const todayClosed = allClosed(data, dayKey(today), habits);
  let date = todayClosed ? today : addDays(today, -1);
  let count = 0;
  while (count < 3700 && allClosed(data, dayKey(date), habits)) {
    count += 1;
    date = addDays(date, -1);
  }
  return { count, todayClosed };
}

// The sample year: made up from a seed per habit, so it is the same on every load of the same day.
function seeded(text) {
  let h = 2166136261;
  for (const ch of text) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
  return () => {
    h += 0x6d2b79f5;
    let t = h;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function sampleYear(habits, today) {
  const data = { days: {}, counts: {} };
  const SPAN = 380;
  const RUN = 23;
  habits.forEach((habit, index) => {
    const random = seeded(`${habit.id}:${index}`);
    const lean = (random() - 0.5) * 0.2;
    const week = Array.from({ length: 7 }, () => 0.7 + random() * 0.45);
    let before = false;
    for (let back = SPAN; back >= 1; back -= 1) {
      const key = dayKey(addDays(today, -back));
      let done;
      if (back <= RUN) done = true;
      else if (back === RUN + 1) done = index !== Math.min(1, habits.length - 1);
      else {
        const grown = 1 - back / SPAN;
        const base = (0.26 + 0.44 * grown + lean) * week[addDays(today, -back).getDay()];
        done = random() < (before ? Math.min(0.93, base + 0.2) : base - 0.12);
      }
      before = done;
      if (done) setCount(data, key, habit, goal(habit), habits);
      else if (habit.target) setCount(data, key, habit, Math.floor(random() * habit.target * 0.8), habits);
    }
    const key = dayKey(today);
    if (habit.target) setCount(data, key, habit, Math.round(habit.target * 0.62), habits);
    else if (index < habits.length - 1 || habits.length === 1) setCount(data, key, habit, 1, habits);
  });
  return data;
}
