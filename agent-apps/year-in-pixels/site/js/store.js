// What the person colors lives in this browser: localStorage "year-in-pixels" holds { "YYYY-MM-DD": { mood, note } },
// mood being 1 (the roughest of the five) to 5 (the best). sessionStorage remembers the open picker.
import { DAY_RE } from "./dates.js";

const KEY = "year-in-pixels";
const PICKER_KEY = "year-in-pixels:picker";
let memory = null;

function storage(kind) {
  try {
    const s = window[kind];
    s.getItem(KEY);
    return s;
  } catch {
    return null;
  }
}

// Keeps only well-formed days: a real date, a mood from 1 to 5, a note of one line.
export function clean(value) {
  const source = value && typeof value === "object" && value.days && typeof value.days === "object" ? value.days : value;
  const out = {};
  if (!source || typeof source !== "object" || Array.isArray(source)) return out;
  for (const [day, entry] of Object.entries(source)) {
    if (!DAY_RE.test(day) || !entry || typeof entry !== "object") continue;
    const mood = Number(entry.mood);
    if (!Number.isInteger(mood) || mood < 1 || mood > 5) continue;
    const note = typeof entry.note === "string" ? entry.note.replace(/\s+/g, " ").trim().slice(0, 120) : "";
    out[day] = note ? { mood, note } : { mood };
  }
  return out;
}

const ordered = (days) => Object.fromEntries(Object.keys(days).sort().map((k) => [k, days[k]]));

// null when this browser has never saved a day, so the first open can start from the example year.
export function loadDays() {
  const s = storage("localStorage");
  if (!s) return memory;
  const raw = s.getItem(KEY);
  if (raw === null) return null;
  try {
    return clean(JSON.parse(raw));
  } catch {
    return {};
  }
}

export function saveDays(days) {
  const s = storage("localStorage");
  memory = ordered(days);
  if (s) s.setItem(KEY, JSON.stringify(memory));
}

export const picker = {
  get() {
    const s = storage("sessionStorage");
    return s ? s.getItem(PICKER_KEY) : null;
  },
  set(value) {
    const s = storage("sessionStorage");
    if (!s) return;
    if (value === null) s.removeItem(PICKER_KEY);
    else s.setItem(PICKER_KEY, value);
  },
};

export function exportFile(days, config) {
  const body = {
    app: "year-in-pixels",
    name: config.name,
    moods: config.moods.map((m, i) => ({ mood: i + 1, id: m.id, label: m.label, color: m.color })),
    days: ordered(days),
  };
  return new Blob([JSON.stringify(body, null, 2) + "\n"], { type: "application/json" });
}
