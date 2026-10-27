// The habit icons, drawn on a 24-unit grid with round strokes. The names match the "icon" values run.py accepts.
const PATHS = {
  water: '<path d="M12 3.5c3.3 4 5.6 7.2 5.6 10.1a5.6 5.6 0 0 1-11.2 0C6.4 10.7 8.7 7.5 12 3.5z"/><path d="M9.4 14.2a2.7 2.7 0 0 0 2.4 2.6"/>',
  run: '<circle cx="15.5" cy="4.6" r="1.9"/><path d="M8.5 9.6l3.4-1.8 2.8 1.6 1.8 3 2.6.8"/><path d="M11.9 7.8l-1.4 5.1 3.3 2.3-1 4.8"/><path d="M10.5 12.9l-2 3.6-3.6.6"/>',
  walk: '<circle cx="12.5" cy="4.5" r="1.9"/><path d="M12.2 8.3l-1.4 6 2.4 2.6.8 4.1"/><path d="M10.8 14.3l-1.6 3.1-1.7 3.6"/><path d="M12.2 8.3l2.6 2.6 2.4.6M12.2 8.3l-3 2-1 3"/>',
  bike: '<circle cx="6" cy="16" r="3.6"/><circle cx="18" cy="16" r="3.6"/><path d="M6 16l3.8-6.5h5.4L18 16M9.8 9.5l3.6 6.5H6"/><path d="M13.6 6h2.6"/>',
  lift: '<path d="M6.5 7v10M17.5 7v10M3.5 9.5v5M20.5 9.5v5M6.5 12h11"/>',
  stretch: '<circle cx="12" cy="4.6" r="1.9"/><path d="M4.5 7.8l7.5 2.4 7.5-2.4"/><path d="M12 10.2v4.6l-3.6 5.7M12 14.8l3.6 5.7"/>',
  breathe: '<path d="M3.5 9h10.2a2.8 2.8 0 1 0-2.8-2.8"/><path d="M3.5 15h13.3a2.8 2.8 0 1 1-2.8 2.8"/><path d="M3.5 12h16.5"/>',
  read: '<path d="M12 6.6C10.2 5.3 7.7 4.6 4.5 4.6v13c3.2 0 5.7.7 7.5 2 1.8-1.3 4.3-2 7.5-2v-13c-3.2 0-5.7.7-7.5 2z"/><path d="M12 6.6v13"/>',
  write: '<path d="M15.6 4.4l4 4L9 19H5v-4z"/><path d="M13.4 6.6l4 4"/>',
  sleep: '<path d="M19.5 14.6A8 8 0 0 1 9.4 4.5a8 8 0 1 0 10.1 10.1z"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.8v2.1M12 19.1v2.1M2.8 12h2.1M19.1 12h2.1M5.5 5.5l1.5 1.5M17 17l1.5 1.5M5.5 18.5L7 17M17 7l1.5-1.5"/>',
  leaf: '<path d="M5 19.5C5 11 10 5 20 4.5c0 10-5.6 15-14 15z"/><path d="M5 19.5l7.5-7.5"/>',
  sprout: '<path d="M12 20.5v-8"/><path d="M12 12.5C12 9 9.6 6.6 5 6.6c0 3.5 2.5 5.9 7 5.9zM12 12.5c0-4.4 3-7.3 7.4-7.3 0 4.4-3 7.3-7.4 7.3z"/><path d="M7.5 20.5h9"/>',
  cup: '<path d="M5 8.5h11.5v5.6a5 5 0 0 1-5 5h-1.5a5 5 0 0 1-5-5z"/><path d="M16.5 10.2h1.6a2.4 2.4 0 0 1 0 4.8h-1.6"/><path d="M9 3.5v2.2M12.5 3.5v2.2"/>',
  pill: '<path d="M10.6 20.2a4.8 4.8 0 0 1-6.8-6.8l6-6a4.8 4.8 0 0 1 6.8 6.8z"/><path d="M7.8 10.4l5.8 5.8"/>',
  heart: '<path d="M12 20s-7.6-4.6-7.6-10.2A4.2 4.2 0 0 1 12 7.4a4.2 4.2 0 0 1 7.6 2.4C19.6 15.4 12 20 12 20z"/>',
  music: '<path d="M9 17.5V5.5l10.5-2v12"/><circle cx="6.5" cy="17.5" r="2.5"/><circle cx="17" cy="15.5" r="2.5"/>',
  code: '<path d="M8 7.5L3.5 12 8 16.5M16 7.5l4.5 4.5-4.5 4.5M13.5 5l-3 14"/>',
  talk: '<path d="M4.5 5.5h15v10.5h-8.2l-4.6 3.6V16H4.5z"/><path d="M8.5 10.8h7"/>',
  "no-phone": '<rect x="7" y="3" width="10" height="18" rx="2.2"/><path d="M11 17.6h2"/><path d="M4 4l16 16"/>',
  spark: '<path d="M12 3.5l1.9 5.6 5.6 1.9-5.6 1.9L12 18.5l-1.9-5.6L4.5 11l5.6-1.9z"/><path d="M18.5 16.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
};

const NS = "http://www.w3.org/2000/svg";

/** An inline SVG icon element for `name`; null when the name is not one of ours. */
export function icon(name, className = "icon") {
  const paths = PATHS[name];
  if (!paths) return null;
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", className);
  svg.setAttribute("aria-hidden", "true");
  svg.innerHTML = paths;
  return svg;
}

/** The habit's icon, or its first letter when the name is unknown. */
export function glyph(habit) {
  const svg = icon(habit.icon);
  if (svg) return svg;
  const letter = document.createElement("b");
  letter.textContent = (habit.label || habit.id || "?").trim().charAt(0).toUpperCase();
  letter.setAttribute("aria-hidden", "true");
  return letter;
}
