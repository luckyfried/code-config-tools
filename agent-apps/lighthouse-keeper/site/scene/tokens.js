// Reads the theme's tokens from theme.css so the sea, sky, fog, beam, and ships take the theme's colors.
import * as THREE from "three";

const COLORS = {
  skyTop: "--sky-top",
  skyHorizon: "--sky-horizon",
  skyGlow: "--sky-glow",
  fog: "--fog",
  seaDeep: "--sea-deep",
  seaShallow: "--sea-shallow",
  seaFoam: "--sea-foam",
  seaSpec: "--sea-spec",
  moon: "--moon",
  beam: "--beam",
  lamp: "--lamp",
  lantern: "--lantern",
  ship: "--ship",
  shipRim: "--ship-rim",
  burnEdge: "--burn-edge",
  tower: "--tower",
  towerBand: "--tower-band",
  towerTrim: "--tower-trim",
  rock: "--rock",
  window: "--window",
  rain: "--rain",
  dawnTop: "--dawn-top",
  dawnHorizon: "--dawn-horizon",
};

const NUMBERS = {
  moonElev: ["--moon-elev", 15],
  moonBearing: ["--moon-bearing", 20],
  stars: ["--stars", 1],
  rainAmount: ["--rain-amount", 0.4],
  fogDensity: ["--fog-density", 0.01],
  fogLayer: ["--fog-layer", 1],
  seaRough: ["--sea-rough", 1],
  thunderEvery: ["--thunder-every", 24],
  exposure: ["--exposure", 1],
  ambient: ["--ambient", 0.35],
  moonLight: ["--moon-light", 0.6],
  beamPower: ["--beam-power", 1],
};

export function readTokens() {
  const style = getComputedStyle(document.documentElement);
  const tokens = { dark: matchMedia("(prefers-color-scheme: dark)").matches };
  for (const [key, name] of Object.entries(COLORS)) {
    const raw = style.getPropertyValue(name).trim();
    tokens[key] = new THREE.Color(raw || "gray");
  }
  for (const [key, [name, fallback]] of Object.entries(NUMBERS)) {
    const value = parseFloat(style.getPropertyValue(name));
    tokens[key] = Number.isFinite(value) ? value : fallback;
  }
  tokens.cssLamp = style.getPropertyValue("--lamp").trim();
  tokens.cssTower = style.getPropertyValue("--tower").trim();
  tokens.cssTrim = style.getPropertyValue("--tower-trim").trim();
  return tokens;
}
