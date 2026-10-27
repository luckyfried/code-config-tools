// Everything the game keeps stays on this device, under keys that start with the app's name.
const PREFIX = "merge-cubes:";

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
    // A full or blocked store: the game plays on without saving.
  }
}

export function forget(key) {
  try {
    localStorage.removeItem(PREFIX + key);
  } catch {
    // Nothing to remove.
  }
}
