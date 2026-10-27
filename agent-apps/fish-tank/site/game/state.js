// The person's tank, kept in localStorage under one key: pearls, fish, decor, tank size, the look, the day length,
// sound, and where the day cycle started. Written on every change and once a minute.
import { STARTING_PEARLS, newFish } from "../sim/economy.js";

const KEY = "fish-tank:save";

export function readSave() {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function writeSave(save) {
  try {
    localStorage.setItem(KEY, JSON.stringify(save));
  } catch {
    // a private window without storage keeps the tank for this visit only
  }
}

// The noon of the day cycle: a light screen opens the tank at noon, a dark one at night.
export function anchorFor(now, cycleMinutes, night) {
  const cycle = cycleMinutes * 60000;
  return night ? now - cycle * 0.5 : now;
}

export function freshSave(config, catalog, now, night) {
  let nextId = 1;
  const fish = [];
  for (const name of config.startingFish) {
    const spec = catalog.species.find((s) => s.name.toLowerCase() === name.toLowerCase());
    if (!spec) continue;
    for (let k = 0; k < spec.group; k++) fish.push(newFish(spec.id, now, nextId++, k));
  }
  return {
    theme: config.theme,
    stamp: stampOf(config),
    pearls: STARTING_PEARLS,
    tank: "small",
    decor: [...catalog.themes[config.theme].decor],
    fish,
    nextId,
    look: "auto",
    cycleMinutes: config.cycleMinutes,
    sound: config.sound,
    anchor: anchorFor(now, config.cycleMinutes, night),
    lastSeen: now,
    firstVisit: true,
  };
}

export function stampOf(config) {
  return JSON.stringify([config.startingFish, config.cycleMinutes, config.sound, config.pearlRate]);
}

// A save from another theme starts a new tank; new inputs for the same theme carry the day length and sound over.
export function reconcile(save, config, catalog, now, night) {
  if (!save || save.theme !== config.theme || !Array.isArray(save.fish)) return freshSave(config, catalog, now, night);
  const known = new Set(catalog.species.map((s) => s.id));
  const next = { ...save, fish: save.fish.filter((f) => known.has(f.sp)), firstVisit: false };
  if (save.stamp !== stampOf(config)) {
    next.stamp = stampOf(config);
    next.cycleMinutes = config.cycleMinutes;
    next.sound = config.sound;
  }
  return next;
}
