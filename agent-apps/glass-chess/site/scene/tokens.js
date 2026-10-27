// Reads the theme's tokens from the page, so a theme file recolors the board, the glass, and the light as well as
// the panels.
import * as THREE from "three";

export function readTokens() {
  const style = getComputedStyle(document.documentElement);
  const css = (name) => style.getPropertyValue(name).trim();
  return {
    css,
    color: (name) => new THREE.Color(css(name) || "#808080"),
    number: (name, fallback = 1) => {
      const v = parseFloat(css(name));
      return Number.isFinite(v) ? v : fallback;
    },
  };
}
