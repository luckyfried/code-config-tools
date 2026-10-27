// What the person chose on this page (platform, Learn, the search) lives on this device under one key.

const KEY = "cheat-sheet";

export function load() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

export function save(patch) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ ...load(), ...patch }));
  } catch {
    // A browser with storage turned off keeps the choice for this visit only.
  }
}
