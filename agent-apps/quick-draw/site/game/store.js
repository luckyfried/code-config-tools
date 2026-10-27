// What the game keeps on this device: the best solo reaction and the sound setting. Nothing leaves the browser.
const PREFIX = "quick-draw:";

function read(key, fallback) {
  try {
    const raw = localStorage.getItem(PREFIX + key);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

function write(key, value) {
  try {
    localStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    // private mode or storage full: the game plays on without saving
  }
}

export const store = {
  best: () => read("best", null),
  setBest: (ms) => write("best", ms),
  muted: () => read("muted", false),
  setMuted: (on) => write("muted", on),
};
