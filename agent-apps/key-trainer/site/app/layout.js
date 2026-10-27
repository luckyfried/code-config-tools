// A keyboard layout from site/layouts/: its keys by code and the way from a character to the key that types it.

export const LAYOUTS = ["qwerty", "qwertz", "azerty", "dvorak", "colemak"];

const NAMED = { " ": "space", "\n": "enter", "\t": "tab" };

export async function loadLayout(id) {
  const name = LAYOUTS.includes(id) ? id : "qwerty";
  const answer = await fetch(`./layouts/${name}.json`);
  if (!answer.ok) throw new Error(`The ${name} layout did not load.`);
  return indexLayout(await answer.json());
}

/** Adds the lookups to a layout: keys by code, and each character to { key, level } where level is base, shift, or alt. */
export function indexLayout(layout) {
  const byCode = new Map();
  const byChar = new Map();
  layout.rows.forEach((row) => {
    row.forEach((key) => {
      byCode.set(key.code, key);
      if (key.base) add(byChar, key.base, key, "base");
      if (key.shift && key.shift !== key.base) add(byChar, key.shift, key, "shift");
      if (key.alt) add(byChar, key.alt, key, "alt");
    });
  });
  const hasAccents = [..."éèüöäàç"].some((c) => byChar.has(c));
  return { ...layout, byCode, byChar, hasAccents };
}

function add(map, char, key, level) {
  if (!map.has(char)) map.set(char, { key, level });
}

/** The letter without its accent: é to e, Ü to U. */
export function bare(char) {
  return char.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

/** Where a character lives on this layout, falling back to its bare letter when the layout has no key for it. */
export function locate(layout, char) {
  return layout.byChar.get(char) || layout.byChar.get(bare(char)) || null;
}

/** Whether a typed character counts for the expected one: the same, or its bare letter when the layout lacks the accent. */
export function matches(layout, typed, expected) {
  if (typed === expected) return true;
  if (layout.byChar.has(expected)) return false;
  return typed === bare(expected);
}

/** The name a key's statistics are kept under: its base legend in lower case, or space, enter, and tab. */
export function statName(layout, char) {
  if (NAMED[char]) return NAMED[char];
  const spot = locate(layout, char);
  if (!spot) return bare(char).toLowerCase();
  const base = spot.key.base;
  return NAMED[base] || base.toLowerCase();
}

/** The key code a statistics name points at on this layout. */
export function codeForStat(layout, name) {
  if (name === "space") return "Space";
  if (name === "enter") return "Enter";
  if (name === "tab") return "Tab";
  const spot = layout.byChar.get(name) || layout.byChar.get(name.toUpperCase());
  return spot ? spot.key.code : null;
}

/** How a statistics name reads on a keycap chip. */
export function capLabel(name) {
  if (name === "space") return "space";
  if (name === "enter") return "enter";
  if (name === "tab") return "tab";
  return name.length === 1 && name.toUpperCase() !== name ? name.toUpperCase() : name;
}
