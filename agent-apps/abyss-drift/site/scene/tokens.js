// Reads the theme's tokens so the world takes its palette from theme.css, the same place the HUD does.
import * as THREE from "three";

const WORLD = [
  "water-surface", "water-mid", "water-deep", "water-abyss", "sun", "caustic", "rock-light", "rock-dark", "lichen",
  "glow", "glow-2", "lure", "vent", "snow", "headlight", "sub-hull",
];

export function readTokens() {
  const css = getComputedStyle(document.documentElement);
  const color = (name, fallback) => {
    const raw = css.getPropertyValue(name).trim();
    const c = new THREE.Color();
    try {
      c.setStyle(raw || fallback);
    } catch {
      c.setStyle(fallback);
    }
    return c;
  };
  const world = {};
  for (const name of WORLD) world[camel(name)] = color(`--world-${name}`, "#4ce8ff");
  return {
    world,
    ui: {
      text: css.getPropertyValue("--color-text").trim(),
      accent: css.getPropertyValue("--color-accent").trim(),
      bg: css.getPropertyValue("--color-bg").trim(),
    },
  };
}

/** Whether the page shows its dark scheme: an explicit data-theme wins over the system setting. */
export function isDark() {
  const set = document.documentElement.dataset.theme;
  if (set === "dark" || set === "light") return set === "dark";
  return matchMedia("(prefers-color-scheme: dark)").matches;
}

function camel(name) {
  return name.replace(/-(\w)/g, (_, c) => c.toUpperCase());
}
