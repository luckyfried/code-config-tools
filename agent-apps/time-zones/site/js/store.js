// The person's choices (the picked date and time, the look, and whether the first glide has played) live under one key.
const KEY = "time-zones";

export function load() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

export function save(value) {
  try { localStorage.setItem(KEY, JSON.stringify(value)); } catch {}
}
