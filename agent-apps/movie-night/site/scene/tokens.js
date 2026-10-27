// The theme's tokens as the scene reads them: every color in the room comes from theme.css.
import { Color } from "three";

const COLORS = [
  "scene-sky-top",
  "scene-sky-bottom",
  "scene-fold",
  "scene-fold-light",
  "scene-floor",
  "scene-fog",
  "scene-rim",
  "scene-beam",
  "scene-dust",
  "scene-pool",
  "scene-dim-color",
  "scene-frame",
];
const NUMBERS = [
  "scene-backdrop",
  "scene-reflect",
  "scene-rim-strength",
  "scene-halo",
  "scene-beam-strength",
  "scene-additive",
  "scene-dim",
  "scene-room-dim",
  "scene-key",
  "scene-shadow",
  "scene-stars",
];

const camel = (name) => name.replace(/^scene-/, "").replace(/-([a-z])/g, (_, c) => c.toUpperCase());

export function readTokens() {
  const cs = getComputedStyle(document.documentElement);
  const t = {};
  for (const name of COLORS) t[camel(name)] = new Color(cs.getPropertyValue(`--${name}`).trim() || "black");
  for (const name of NUMBERS) {
    const v = parseFloat(cs.getPropertyValue(`--${name}`));
    t[camel(name)] = Number.isFinite(v) ? v : 0;
  }
  return t;
}

export function readCss(names) {
  const cs = getComputedStyle(document.documentElement);
  const out = {};
  for (const name of names) out[name] = cs.getPropertyValue(`--${name}`).trim();
  return out;
}
