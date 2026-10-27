// Reads the theme's world tokens from the page, so a theme recolors the sky, the ground, the funnel, and every prop.
import * as THREE from "three";

const COLORS = [
  "sky-zenith", "sky-horizon", "sky-band", "cloud-dark", "cloud-light", "fog", "sun", "hemi-sky", "hemi-ground",
  "ground-pasture", "ground-pasture-2", "ground-crop-a", "ground-crop-b", "ground-crop-c", "ground-crop-d",
  "ground-road", "ground-lane", "ground-yard", "ground-lawn", "ground-hill", "grass-tip",
  "funnel-top", "funnel-bottom", "funnel-glow", "debris-a", "debris-b", "debris-c", "dust", "rain", "bolt", "spark",
  "flash-light", "tower-paint", "tower-ink",
  "prop-barn", "prop-trim", "prop-roof", "prop-wood", "prop-leaf", "prop-pine", "prop-cow", "prop-spot", "prop-hay",
  "prop-car-a", "prop-car-b", "prop-window", "prop-tire", "prop-house", "prop-metal", "prop-house-b",
];
const NUMBERS = [
  "sky-band-strength", "cloud-cover", "fog-near", "fog-far", "sun-intensity", "sun-elevation", "hemi-intensity",
  "exposure", "funnel-opacity", "funnel-light", "rain-alpha", "prop-window-glow", "grass-height",
];

// The order of the prop palette: props.js names each part by one of these, and the prop shader reads the color here.
export const PALETTE = [
  "prop-barn", "prop-trim", "prop-roof", "prop-wood", "prop-leaf", "prop-pine", "prop-cow", "prop-spot", "prop-hay",
  "prop-car-a", "prop-car-b", "prop-window", "prop-tire", "prop-house", "prop-metal", "prop-house-b",
];
export const PAL = Object.fromEntries(PALETTE.map((name, i) => [name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase()), i]));

const camel = (name) => name.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());

export function readTokens() {
  const css = getComputedStyle(document.documentElement);
  const colors = {};
  for (const name of COLORS) {
    const value = css.getPropertyValue(`--${name}`).trim();
    colors[camel(name)] = new THREE.Color(value || "#808080");
  }
  const numbers = {};
  for (const name of NUMBERS) {
    const value = parseFloat(css.getPropertyValue(`--${name}`));
    numbers[camel(name)] = Number.isFinite(value) ? value : 0;
  }
  const hex = {};
  for (const name of ["tower-paint", "tower-ink"]) hex[camel(name)] = css.getPropertyValue(`--${name}`).trim() || "#ffffff";
  return { colors, numbers, hex };
}
