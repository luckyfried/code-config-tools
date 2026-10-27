// What the page keeps in this browser: drill results under key-trainer:v1 and the person's settings under
// key-trainer:settings. With no drills yet, a sample month stands in, marked as a sample wherever it shows.

import { seeded } from "./text.js";

const HISTORY = "key-trainer:v1";
const SETTINGS = "key-trainer:settings";
const DAY = 86400000;

/** The minimum presses of a key before its own error rate carries its color by itself. */
export const SETTLED = 50;

export function readHistory() {
  try {
    const rows = JSON.parse(localStorage.getItem(HISTORY) || "[]");
    return Array.isArray(rows) ? rows.filter(validRow) : [];
  } catch (error) {
    return [];
  }
}

export function writeHistory(rows) {
  try {
    localStorage.setItem(HISTORY, JSON.stringify(rows));
    return true;
  } catch (error) {
    return false;
  }
}

export function addDrill(row) {
  const rows = readHistory();
  rows.push(row);
  writeHistory(rows);
  return rows;
}

export function validRow(row) {
  return (
    row &&
    typeof row === "object" &&
    typeof row.date === "string" &&
    !Number.isNaN(Date.parse(row.date)) &&
    Number.isFinite(row.wpm) &&
    Number.isFinite(row.accuracy) &&
    row.errorsByKey &&
    typeof row.errorsByKey === "object"
  );
}

/** Adds rows from an exported file, skipping any already here; answers how many were new. */
export function importRows(rows) {
  const have = readHistory();
  const seen = new Set(have.map((r) => `${r.date}|${r.wpm}|${r.accuracy}`));
  let added = 0;
  for (const row of rows) {
    if (!validRow(row)) continue;
    const id = `${row.date}|${row.wpm}|${row.accuracy}`;
    if (seen.has(id)) continue;
    seen.add(id);
    have.push(row);
    added += 1;
  }
  have.sort((a, b) => Date.parse(a.date) - Date.parse(b.date));
  writeHistory(have);
  return added;
}

export function readSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS) || "{}");
    return saved && typeof saved === "object" ? saved : {};
  } catch (error) {
    return {};
  }
}

export function writeSettings(patch) {
  const next = { ...readSettings(), ...patch };
  try {
    localStorage.setItem(SETTINGS, JSON.stringify(next));
  } catch (error) {
    // A full or blocked store keeps the settings for this visit only.
  }
  return next;
}

/** Local calendar day of a date, as YYYY-MM-DD. */
export function dayKey(date) {
  const d = new Date(date);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** The last 30 days, oldest first: each with its drills, mean WPM and accuracy, and whether any drill was on touch. */
export function lastDays(rows, now = Date.now()) {
  const days = [];
  const today = new Date(now);
  today.setHours(12, 0, 0, 0);
  const byDay = new Map();
  rows.forEach((row) => {
    const key = dayKey(row.date);
    if (!byDay.has(key)) byDay.set(key, []);
    byDay.get(key).push(row);
  });
  for (let i = 29; i >= 0; i -= 1) {
    const date = new Date(today.getTime() - i * DAY);
    const key = dayKey(date);
    const drills = byDay.get(key) || [];
    const mean = (pick) => (drills.length ? drills.reduce((s, r) => s + pick(r), 0) / drills.length : null);
    days.push({
      key,
      date,
      drills,
      wpm: mean((r) => r.wpm),
      accuracy: mean((r) => r.accuracy),
      touch: drills.some((r) => r.input === "touch"),
    });
  }
  return days;
}

export function totals(rows, now = Date.now()) {
  const recent = rows.filter((r) => now - Date.parse(r.date) < 30 * DAY);
  const seconds = recent.reduce((s, r) => s + (r.seconds || 60), 0);
  const best = recent.reduce((m, r) => Math.max(m, r.wpm), 0);
  const acc = recent.length ? recent.reduce((s, r) => s + r.accuracy, 0) / recent.length : 0;
  return { drills: recent.length, minutes: Math.round(seconds / 60), best: Math.round(best), accuracy: acc };
}

/** Presses and errors per key, pooled over the last 30 days of rows. */
export function pool(rows, now = Date.now()) {
  const samples = new Map();
  const errors = new Map();
  rows
    .filter((r) => now - Date.parse(r.date) < 30 * DAY)
    .forEach((r) => {
      for (const [k, v] of Object.entries(r.samplesByKey || {})) samples.set(k, (samples.get(k) || 0) + v);
      for (const [k, v] of Object.entries(r.errorsByKey || {})) {
        errors.set(k, (errors.get(k) || 0) + v);
        if (!r.samplesByKey) samples.set(k, (samples.get(k) || 0) + Math.max(v, SETTLED));
      }
    });
  return { samples, errors };
}

/**
 * Heat per key name, 0 to 1. A key's rate is weighed against fifty clean presses, so a key with a handful of
 * presses can only warm a little, and its color settles on its own record once it has fifty.
 */
export function heatByName(pooled) {
  const heat = new Map();
  for (const [name, n] of pooled.samples) {
    const e = pooled.errors.get(name) || 0;
    if (!n || !e) continue;
    const rate = n >= SETTLED ? e / n : e / (n + SETTLED);
    const value = Math.max(0.14, Math.min(1, Math.pow(rate / 0.16, 1.2)));
    heat.set(name, n >= SETTLED ? value : Math.min(0.5, value));
  }
  return heat;
}

/** The weakest keys, by the same weighed rate the heat map shows, each with its rate and presses. */
export function weakKeys(pooled, count = 5) {
  const list = [];
  for (const [name, n] of pooled.samples) {
    const e = pooled.errors.get(name) || 0;
    if (!e) continue;
    const rate = n >= SETTLED ? e / n : e / (n + SETTLED);
    list.push({ name, char: name === "space" ? " " : name, rate, raw: e / n, samples: n, errors: e });
  }
  return list.sort((a, b) => b.rate - a.rate).slice(0, count);
}

const FREQ = {
  e: 12.7, t: 9.1, a: 8.2, o: 7.5, i: 7.0, n: 6.7, s: 6.3, h: 6.1, r: 6.0, d: 4.3, l: 4.0, c: 2.8, u: 2.8, m: 2.4,
  w: 2.4, f: 2.2, g: 2.0, y: 2.0, p: 1.9, b: 1.5, v: 1.0, k: 0.8, j: 0.15, x: 0.15, q: 0.1, z: 0.07, ".": 1.1, ",": 1.2,
  "'": 0.3, space: 18,
};
const WEAK = { b: 4.2, y: 3.1, p: 2.6, q: 3.8, x: 3.4, z: 2.8, v: 2.2, ",": 2.4, "'": 2.2, m: 1.7, j: 2.4 };

/** A month of drills for a page with none yet, the same on every visit on a given day. */
export function sampleMonth(now = Date.now()) {
  const rand = seeded(20261021);
  const rows = [];
  const today = new Date(now);
  today.setHours(8, 10, 0, 0);
  const total = Object.values(FREQ).reduce((s, v) => s + v, 0);
  // The month runs to yesterday, so today's point is the one a drill draws onto the line.
  for (let i = 29; i >= 1; i -= 1) {
    const skip = rand() < 0.2 && i > 2;
    const count = skip ? 0 : 1 + Math.floor(rand() * 2.4);
    for (let n = 0; n < count; n += 1) {
      const d = 29 - i;
      const wpm = 49 + d * 0.62 + (rand() - 0.5) * 7 + n * 1.5;
      const accuracy = Math.min(0.99, 0.918 + d * 0.0013 + (rand() - 0.5) * 0.02);
      const chars = Math.round(wpm * 5);
      const samplesByKey = {};
      const errorsByKey = {};
      let weightSum = 0;
      for (const [k, f] of Object.entries(FREQ)) weightSum += f * (WEAK[k] || 1);
      const totalErrors = Math.round(chars * (1 - accuracy));
      for (const [k, f] of Object.entries(FREQ)) {
        const s = Math.max(0, Math.round((chars * f) / total + (rand() - 0.5) * 2));
        if (s) samplesByKey[k] = s;
        const e = Math.round((totalErrors * f * (WEAK[k] || 1)) / weightSum + (rand() - 0.6));
        if (e > 0) errorsByKey[k] = Math.min(e, s || e);
      }
      const date = new Date(today.getTime() - i * DAY + n * 3600000 * 3.5);
      rows.push({
        date: date.toISOString(),
        mode: n === 1 && d % 4 === 0 ? "weak" : "prose",
        layout: "qwerty",
        input: d % 9 === 4 ? "touch" : "keys",
        seconds: 60,
        wpm: Math.round(wpm * 10) / 10,
        accuracy: Math.round(accuracy * 1000) / 1000,
        chars,
        errorsByKey,
        samplesByKey,
      });
    }
  }
  return rows;
}
