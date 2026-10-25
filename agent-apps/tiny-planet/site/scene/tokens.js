// Reads the theme's world tokens from the page so a theme recolors the planet, the sky, and the explorer.
import * as THREE from "three";

const COLOR_TOKENS = [
  "world-floor", "world-shore", "world-meadow", "world-forest", "world-rock", "world-snow", "world-sea",
  "world-sea-deep", "world-foam", "world-trunk", "world-leaf", "world-leaf-2", "world-grass", "world-stone",
  "world-dust", "sky-noon-zenith", "sky-noon-horizon", "sky-dusk-zenith", "sky-dusk-horizon", "sky-night-zenith",
  "sky-night-horizon", "sun-noon", "sun-dusk", "moon", "rim", "crystal", "explorer-body", "explorer-scarf",
  "explorer-pack",
];
const NUMBER_TOKENS = ["world-sea-glow", "world-snowline", "world-land-bias", "world-title-phase"];

const camel = (name) => name.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());

export function readTokens() {
  const css = getComputedStyle(document.documentElement);
  const colors = {};
  for (const name of COLOR_TOKENS) {
    const value = css.getPropertyValue(`--${name}`).trim();
    colors[camel(name)] = new THREE.Color(value || "#ff00ff");
  }
  const numbers = {};
  for (const name of NUMBER_TOKENS) {
    const value = parseFloat(css.getPropertyValue(`--${name}`));
    numbers[camel(name)] = Number.isFinite(value) ? value : 0;
  }
  return { colors, numbers };
}
