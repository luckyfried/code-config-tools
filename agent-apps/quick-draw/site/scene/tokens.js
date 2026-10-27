// Reads the theme's --scene-* tokens, so a theme file recolors the street, the sky, the light, and the two gunslingers.
import { Color } from "three";

const COLORS = [
  "sky-zenith", "sky-mid", "sky-horizon", "sun", "sun-glow", "light", "ambient-sky", "ambient-ground", "fog",
  "ground", "ground-rut", "mesa", "wood", "wood-light", "paint-1", "paint-2", "paint-3", "paint-4", "paint-5",
  "trim", "window", "lantern", "cloud", "p1-coat", "p1-accent", "p1-hat", "p2-coat", "p2-accent", "p2-hat",
  "skin", "dust", "rim", "figure-fill",
];
const NUMBERS = [
  "sun-elevation", "sun-azimuth", "sun-size", "light-intensity", "ambient-intensity", "fog-near", "fog-far",
  "lantern-on", "stars", "moon", "exposure", "shimmer", "bloom", "rim-intensity", "rim-tint",
  "figure-fill-intensity",
];

const camel = (name) => name.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());

export function readTokens(root = document.documentElement) {
  const style = getComputedStyle(root);
  const tokens = {};
  for (const name of COLORS) {
    const raw = style.getPropertyValue(`--scene-${name}`).trim() || "#888888";
    tokens[camel(name)] = new Color(raw.slice(0, 7));
  }
  for (const name of NUMBERS) {
    const value = parseFloat(style.getPropertyValue(`--scene-${name}`));
    tokens[camel(name)] = Number.isFinite(value) ? value : 0;
  }
  return tokens;
}

/** Hex strings of a few UI tokens, for canvas-drawn signs that should match the page. */
export function readCss(name, root = document.documentElement) {
  return getComputedStyle(root).getPropertyValue(name).trim();
}
