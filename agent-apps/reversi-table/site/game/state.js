// What the device keeps: the game in progress and the person's table, light, and sound choices. Every key starts
// with the app's name so other apps on the same address keep their own.
const GAME = "reversi-table:game";
const PREFS = "reversi-table:prefs";

function read(key) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return value && typeof value === "object" ? value : null;
  } catch (error) {
    return null;
  }
}

function write(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    // Storage is full or blocked: the game plays on without saving.
  }
}

export const loadGame = () => read(GAME);
export const saveGame = (game) => write(GAME, game);
export const clearGame = () => write(GAME, null);
export const loadPrefs = () => read(PREFS) || {};
export const savePrefs = (prefs) => write(PREFS, prefs);
