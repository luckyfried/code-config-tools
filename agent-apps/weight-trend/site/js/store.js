// Everything the person enters lives in this browser under one localStorage key named after the app:
// { entries: [{ date, value, note }], units?, goal? } with every value in kilograms.

import { LB_PER_KG, sampleEntries } from "./trend.js";

const KEY = "weight-trend";
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export function toKg(value, units) {
  return units === "lb" ? value / LB_PER_KG : value;
}

export function fromKg(kg, units) {
  return units === "lb" ? kg * LB_PER_KG : kg;
}

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function createStore(config) {
  let data = read();
  if (!data || !Array.isArray(data.entries)) {
    const goalKg = toKg(config.goal, config.units);
    data = { entries: config.sample ? sampleEntries(goalKg) : [] };
    save();
  }

  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(data));
    } catch {
      /* a full or blocked storage keeps the page working for this visit */
    }
  }

  return {
    get units() {
      return data.units || config.units;
    },
    get goalKg() {
      return typeof data.goal === "number" ? data.goal : toKg(config.goal, config.units);
    },
    get entries() {
      return data.entries;
    },
    setUnits(units) {
      data.units = units;
      save();
    },
    setGoalKg(kg) {
      data.goal = kg;
      save();
    },
    put(date, kg, note) {
      const entry = { date, value: Math.round(kg * 1000) / 1000, note: note.trim() };
      const i = data.entries.findIndex((e) => e.date === date);
      if (i >= 0) data.entries[i] = entry;
      else data.entries.push(entry);
      data.entries.sort((a, b) => (a.date < b.date ? -1 : 1));
      save();
    },
    remove(date) {
      data.entries = data.entries.filter((e) => e.date !== date);
      save();
    },
    exportJson() {
      const units = this.units;
      const entries = data.entries.map((e) => ({
        date: e.date,
        value: Math.round(fromKg(e.value, units) * 10) / 10,
        note: e.note || "",
      }));
      return JSON.stringify({ units, entries }, null, 2);
    },
    // Takes the export's shape, or a bare list of { date, value, note } read in the page's current units.
    // Same dates are replaced, new dates are added. Returns the count taken, or throws a plain-words Error.
    importJson(text) {
      let parsed;
      try {
        parsed = JSON.parse(text);
      } catch {
        throw new Error("That file is not JSON.");
      }
      const list = Array.isArray(parsed) ? parsed : parsed && parsed.entries;
      const units = !Array.isArray(parsed) && parsed && (parsed.units === "kg" || parsed.units === "lb") ? parsed.units : this.units;
      if (!Array.isArray(list)) throw new Error("That file has no list of weigh-ins.");
      const taken = [];
      for (const row of list) {
        const value = Number(row && row.value);
        if (!row || !DATE.test(String(row.date)) || !Number.isFinite(value) || value <= 0) continue;
        taken.push({ date: row.date, value: Math.round(toKg(value, units) * 1000) / 1000, note: String(row.note || "").slice(0, 80) });
      }
      if (!taken.length) throw new Error("That file has no weigh-ins with a date and a value.");
      const byDate = new Map(data.entries.map((e) => [e.date, e]));
      for (const e of taken) byDate.set(e.date, e);
      data.entries = [...byDate.values()].sort((a, b) => (a.date < b.date ? -1 : 1));
      save();
      return taken.length;
    },
  };
}
