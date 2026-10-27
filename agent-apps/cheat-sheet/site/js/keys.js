// Key names to the glyph or word each platform prints on its keys. "mod" is Command on a Mac and Ctrl elsewhere.

const MODIFIERS = new Set(["mod", "cmd", "command", "meta", "super", "win", "ctrl", "control", "alt", "opt", "option", "shift", "fn", "hyper"]);

const MAC = {
  mod: "⌘", cmd: "⌘", command: "⌘", meta: "⌘", super: "⌘", win: "⌘",
  ctrl: "⌃", control: "⌃", alt: "⌥", opt: "⌥", option: "⌥", shift: "⇧", fn: "fn", hyper: "✦",
  enter: "↩", return: "↩", tab: "⇥", backspace: "⌫", delete: "⌦", del: "⌦", esc: "esc", escape: "esc",
  space: "Space", capslock: "⇪", pageup: "⇞", pagedown: "⇟", home: "↖", end: "↘",
  up: "↑", down: "↓", left: "←", right: "→",
};

const PC = {
  mod: "Ctrl", ctrl: "Ctrl", control: "Ctrl", alt: "Alt", opt: "Alt", option: "Alt", shift: "Shift", fn: "Fn",
  hyper: "Hyper", enter: "Enter", return: "Enter", tab: "Tab", backspace: "Backspace", delete: "Del", del: "Del",
  esc: "Esc", escape: "Esc", space: "Space", capslock: "Caps", pageup: "PgUp", pagedown: "PgDn", home: "Home",
  end: "End", up: "↑", down: "↓", left: "←", right: "→",
};

const WINDOWS = { ...PC, cmd: "Win", command: "Win", meta: "Win", super: "Win", win: "Win" };
const LINUX = { ...PC, cmd: "Super", command: "Super", meta: "Super", super: "Super", win: "Super" };

const TABLES = { mac: MAC, windows: WINDOWS, linux: LINUX };

// One cap: the text on it and its kind, which sets its size ("mod" glyphs large, "key" letters, "word" small text).
export function capFor(name, platform) {
  const raw = String(name);
  const lower = raw.trim().toLowerCase();
  const table = TABLES[platform] || MAC;
  const label = table[lower] ?? (raw.length === 1 || /^f\d{1,2}$/.test(lower) ? raw.toUpperCase() : raw);
  const isMod = MODIFIERS.has(lower);
  const isWord = [...label].length > 2 && !/^F\d{1,2}$/i.test(label);
  return { label, kind: isMod ? "mod" : isWord ? "word" : "key", word: isMod && isWord };
}

// Entries carry either one chord (["mod", "shift", "p"]) or a sequence of chords ([["ctrl", "b"], ["%"]]).
export function chordsOf(keys) {
  if (!Array.isArray(keys) || keys.length === 0) return [];
  return Array.isArray(keys[0]) ? keys : [keys];
}

export function keysFor(entry, platform) {
  const own = entry.platforms && entry.platforms[platform];
  return chordsOf(own ?? entry.keys);
}

// The words a person might type to find an entry by its keys ("cmd shift p", "ctrl b").
export function keyWords(entry, platform) {
  return keysFor(entry, platform)
    .flat()
    .map((k) => {
      const lower = String(k).toLowerCase();
      return lower === "mod" ? (platform === "mac" ? "cmd command" : "ctrl") : lower;
    })
    .join(" ");
}
