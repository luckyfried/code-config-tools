// The WebGL renderer. Antialias is on in every tier; the scene's shaders write display colors straight to the screen.
import * as THREE from "three";

export function createRenderer(canvas, tier) {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: "high-performance" });
  if (!renderer.capabilities.isWebGL2) throw new Error("WebGL 2 is needed");
  renderer.setPixelRatio(tier.ratio);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NoToneMapping;
  return renderer;
}

// "#rrggbb" or "#rgb" from the theme, as 0 to 1 display values.
export function hexColor(text, fallback = [0, 0, 0]) {
  const t = (text || "").trim();
  const m = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(t);
  if (!m) return new THREE.Vector3(...fallback);
  let h = m[1];
  if (h.length === 3) h = h.replace(/./g, (c) => c + c);
  const n = parseInt(h, 16);
  return new THREE.Vector3(((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255);
}

export function readTokens() {
  const css = getComputedStyle(document.documentElement);
  const get = (name) => css.getPropertyValue(name).trim();
  const names = ["water", "water-deep", "land", "land-2", "town", "street", "road", "shore", "edge", "tint", "wind", "cloud", "marker"];
  const tokens = {};
  for (const n of names) tokens[n] = hexColor(get(`--map-${n}`));
  tokens.paper = Number(get("--map-paper") || 0) > 0.5 ? 1 : 0;
  return tokens;
}
