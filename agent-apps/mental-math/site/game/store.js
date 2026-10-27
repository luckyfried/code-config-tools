// Results live in this browser under "mental-math:v1" as { <player>: [{ date, score, level, accuracy }] }.
// Choices on Start (the player, each player's level and operations) live under "mental-math:prefs".

import { seeded } from "./problems.js";

const RESULTS_KEY = "mental-math:v1";
const PREFS_KEY = "mental-math:prefs";

function read(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return value && typeof value === "object" && !Array.isArray(value) ? value : fallback;
  } catch {
    return fallback;
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

export function today(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function daysAgo(n, from = new Date()) {
  const d = new Date(from.getFullYear(), from.getMonth(), from.getDate() - n);
  return today(d);
}

export function loadResults() {
  return read(RESULTS_KEY, {});
}

export function entriesFor(name) {
  const all = loadResults();
  return Array.isArray(all[name]) ? all[name].filter(validEntry) : [];
}

export function addResult(name, entry) {
  const all = loadResults();
  const list = Array.isArray(all[name]) ? all[name] : [];
  list.push(entry);
  all[name] = list;
  return write(RESULTS_KEY, all);
}

export function loadPrefs() {
  const prefs = read(PREFS_KEY, {});
  return {
    player: typeof prefs.player === "string" ? prefs.player : null,
    levels: prefs.levels && typeof prefs.levels === "object" ? prefs.levels : {},
    ops: prefs.ops && typeof prefs.ops === "object" ? prefs.ops : {},
  };
}

export function savePrefs(prefs) {
  write(PREFS_KEY, prefs);
}

function validEntry(e) {
  return (
    e &&
    typeof e === "object" &&
    /^\d{4}-\d{2}-\d{2}$/.test(e.date) &&
    Number.isFinite(e.score) &&
    Number.isFinite(e.level) &&
    Number.isFinite(e.accuracy)
  );
}

/** The whole store as a file a person keeps or hands to their agent. */
export function exportText() {
  const all = loadResults();
  const clean = {};
  for (const [name, list] of Object.entries(all)) {
    if (Array.isArray(list)) clean[name] = list.filter(validEntry);
  }
  return JSON.stringify(clean, null, 2) + "\n";
}

/** Merges an exported file into this browser's store; answers how many drills were new, by player. */
export function importText(text) {
  const incoming = JSON.parse(text);
  if (!incoming || typeof incoming !== "object" || Array.isArray(incoming)) throw new Error("shape");
  const all = loadResults();
  const added = {};
  for (const [name, list] of Object.entries(incoming)) {
    if (!Array.isArray(list)) continue;
    const mine = Array.isArray(all[name]) ? all[name] : [];
    const seen = new Set(mine.map((e) => JSON.stringify([e.date, e.score, e.level, e.accuracy])));
    for (const e of list) {
      if (!validEntry(e)) continue;
      const key = JSON.stringify([e.date, e.score, e.level, e.accuracy]);
      if (seen.has(key)) continue;
      seen.add(key);
      mine.push({ date: e.date, score: e.score, level: e.level, accuracy: e.accuracy });
      added[name] = (added[name] || 0) + 1;
    }
    mine.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
    all[name] = mine;
  }
  write(RESULTS_KEY, all);
  return added;
}

/**
 * A sample month for a player with no drills yet, so the curve has a shape before the first one: about twenty
 * days out of thirty, climbing from the player's level. It is never saved and never exported.
 */
export function sampleFor(player) {
  const rand = seeded(`sample:${player.name}`);
  const target = player.level || 3;
  const start = Math.max(1, target - 2);
  const out = [];
  let base = 0;
  for (let n = 29; n >= 1; n -= 1) {
    if (rand() < 0.32) continue;
    base += 0.9 + rand() * 0.8;
    const level = Math.min(target, start + Math.floor(((29 - n) / 28) * (target - start + 1)));
    const accuracy = Math.round(72 + rand() * 24);
    const right = player.kid ? Math.round(6 + rand() * 4) : Math.round(14 + base * 0.45 + rand() * 6);
    out.push({ date: daysAgo(n), score: right * level * 10, level, accuracy });
  }
  return out;
}

/** Best score per day for the thirty days ending today: [{ day: 0..29, date, score }]. */
export function lastThirty(entries) {
  const best = new Map();
  for (const e of entries) {
    if (!best.has(e.date) || best.get(e.date) < e.score) best.set(e.date, e.score);
  }
  const points = [];
  for (let n = 29; n >= 0; n -= 1) {
    const date = daysAgo(n);
    if (best.has(date)) points.push({ day: 29 - n, date, score: best.get(date) });
  }
  return points;
}
