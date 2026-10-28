// The theme's tokens as the scene reads them, so a theme recolors the room, the light, and the generated books.
import { luminance, shade } from "./textures.js";

export function readTokens() {
  const cs = getComputedStyle(document.documentElement);
  const get = (name, fallback) => cs.getPropertyValue(`--${name}`).trim() || fallback;
  const num = (name, fallback) => {
    const v = parseFloat(get(name, ""));
    return Number.isFinite(v) ? v : fallback;
  };
  const accent = get("color-accent", "#c9a05a");
  const ink = get("scene-ink", "#25221c");
  return {
    bg: get("color-bg", "#10201b"),
    text: get("color-text", "#efe7d4"),
    accent,
    wall: get("scene-wall", "#1a2a22"),
    back: get("scene-back", "#13241d"),
    trim: get("scene-trim", "#22362c"),
    floor: get("scene-floor", "#2a1d12"),
    key: get("scene-key", "#ffc27a"),
    keyPower: num("scene-key-power", 40),
    ambient: get("scene-ambient", "#4a6070"),
    ground: get("scene-ground", "#1c140c"),
    hemi: num("scene-hemi", 0.4),
    env: num("scene-env", 0.15),
    exposure: num("scene-exposure", 1),
    window: num("scene-window", 0),
    mote: get("scene-mote", "#ffd49a"),
    motePower: num("scene-mote-power", 1),
    glow: get("scene-glow", "#ffb15a"),
    glowPower: num("scene-glow-power", 1),
    shadow: get("scene-shadow", "#000000"),
    shadowPower: num("scene-shadow-power", 0.6),
    paper: get("scene-paper", "#f1e8d3"),
    ink,
    pageAccent: luminance(accent) > 0.3 ? shade(accent, -0.42) : accent,
    scrim: get("scrim", "#000000"),
    books: [1, 2, 3, 4, 5, 6].map((i) => get(`book-${i}`, "#445566")),
  };
}
