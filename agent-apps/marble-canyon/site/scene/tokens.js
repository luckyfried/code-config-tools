// The scene's palette and light, read from the theme's --scene-* tokens so a theme recolors the world.
import { Color, Vector3 } from "three";

const COLORS = [
  "sky-top",
  "sky-mid",
  "horizon",
  "sun",
  "fog",
  "rock-1",
  "rock-2",
  "rock-3",
  "rock-4",
  "rock-5",
  "floor",
  "track",
  "track-side",
  "lane",
  "kerb-a",
  "kerb-b",
  "boost",
  "gate",
  "glow",
  "ghost",
  "hemi-sky",
  "hemi-ground",
];

const NUMBERS = [
  "exposure",
  "env-intensity",
  "sun-intensity",
  "hemi-intensity",
  "glow-strength",
  "track-env",
  "fog-near",
  "fog-far",
  "sun-x",
  "sun-y",
  "sun-z",
];

const camel = (name) => name.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());

export function readTokens() {
  const style = getComputedStyle(document.documentElement);
  const tokens = {};
  for (const name of COLORS) {
    const raw = style.getPropertyValue(`--scene-${name}`).trim();
    tokens[camel(name)] = new Color(raw || "#888888");
  }
  for (const name of NUMBERS) {
    const raw = parseFloat(style.getPropertyValue(`--scene-${name}`));
    tokens[camel(name)] = Number.isFinite(raw) ? raw : 1;
  }
  tokens.env = style.getPropertyValue("--scene-env").trim() || "canyon-day";
  tokens.sunDir = new Vector3(tokens.sunX, tokens.sunY, tokens.sunZ).normalize();
  tokens.rocks = [tokens.rock1, tokens.rock2, tokens.rock3, tokens.rock4, tokens.rock5];
  tokens.accent = new Color(style.getPropertyValue("--color-accent").trim() || "#ffffff");
  tokens.gold = new Color(style.getPropertyValue("--color-gold").trim() || "#ffcc33");
  tokens.dark = style.colorScheme === "dark" || style.getPropertyValue("color-scheme").trim() === "dark";
  return tokens;
}
