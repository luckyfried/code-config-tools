// What a guest enters stays on this device under one key, event-page:state, and is never sent anywhere.
const KEY = "event-page:state";

export function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
}

export function save(patch) {
  const next = { ...load(), ...patch };
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Private windows can refuse storage; the page still works without it.
  }
  return next;
}
