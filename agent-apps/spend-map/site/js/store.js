// What the person chose (screen, month, table order, look) is kept on this device under one key.
const KEY = "spend-map";

export function load() {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch {
    return {};
  }
}

export function save(state) {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    /* storage is off; the page still works for this visit */
  }
}
