// The best score, the longest streak, and the sound setting stay on this device under the app's own prefix.
const PREFIX = "shard-storm:";

export function load(key, fallback) {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function save(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // Private windows can refuse storage; the run still plays.
  }
}
