// The night's numbers and the best night kept on this machine under one key.
const KEY = "lighthouse-keeper";

export function loadSave() {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "{}");
    return {
      bestTurned: Number(raw.bestTurned) || 0,
      bestSeconds: Number(raw.bestSeconds) || 0,
      dawns: Number(raw.dawns) || 0,
      muted: raw.muted === true,
    };
  } catch {
    return { bestTurned: 0, bestSeconds: 0, dawns: 0, muted: false };
  }
}

export function writeSave(save) {
  try {
    localStorage.setItem(KEY, JSON.stringify(save));
  } catch {
    // A browser that refuses storage keeps the best night for this visit only.
  }
}

export function clock(seconds) {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function recordNight(save, turned, seconds, dawn) {
  const best = turned > save.bestTurned;
  save.bestTurned = Math.max(save.bestTurned, turned);
  save.bestSeconds = Math.max(save.bestSeconds, Math.round(seconds));
  if (dawn) save.dawns += 1;
  writeSave(save);
  return best;
}

const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
export function count(n) {
  return n <= 10 ? WORDS[n] : String(n);
}
