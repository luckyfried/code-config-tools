// Reads the theme's tokens from the page, so a theme file recolors the 3D stage the same way it recolors the page.
import * as THREE from "three";

export const STEPS = 12;

export function readTokens() {
  const css = getComputedStyle(document.documentElement);
  const raw = (name) => css.getPropertyValue(name).trim();
  const color = (name, fallback = "#808080") => new THREE.Color(raw(name) || fallback);
  const num = (name, fallback = 0) => {
    const v = parseFloat(raw(name));
    return Number.isFinite(v) ? v : fallback;
  };
  const cubes = [];
  for (let i = 1; i <= STEPS; i += 1) {
    const fill = color(`--cube-${i}`);
    // --cube-heat-N is the color a cube glows in; a theme that leaves it out glows in the cube's own color.
    const heat = raw(`--cube-heat-${i}`) ? color(`--cube-heat-${i}`) : fill.clone();
    cubes.push({ color: fill, heat, ink: raw(`--cube-ink-${i}`) || "#222222", glow: num(`--cube-glow-${i}`) });
  }
  return {
    dark: css.colorScheme.includes("dark") || raw("color-scheme") === "dark",
    bg: color("--color-bg"),
    skyTop: color("--scene-sky-top"),
    horizon: color("--scene-sky-horizon"),
    floor: color("--scene-floor"),
    floorGlow: color("--scene-floor-glow"),
    floorPattern: raw("--scene-floor-pattern").replace(/"/g, "") || "none",
    floorCss: raw("--scene-floor"),
    floorGlowCss: raw("--scene-floor-glow"),
    bgCss: raw("--color-bg"),
    socketCss: raw("--scene-socket"),
    socketEdgeCss: raw("--scene-socket-edge"),
    trayCss: raw("--scene-tray"),
    bandCss: raw("--scene-band"),
    tray: color("--scene-tray"),
    socket: color("--scene-socket"),
    socketEdge: color("--scene-socket-edge"),
    rim: color("--scene-rim"),
    rimGlow: num("--scene-rim-glow", 1),
    pedestal: color("--scene-pedestal"),
    band: color("--scene-band"),
    bandGlow: num("--scene-band-glow", 1),
    key: color("--scene-key"),
    keyPower: num("--scene-key-power", 2),
    fillSky: color("--scene-fill-sky"),
    fillGround: color("--scene-fill-ground"),
    fillPower: num("--scene-fill-power", 1),
    back: color("--scene-back"),
    backPower: num("--scene-back-power", 1),
    envPower: num("--scene-env-power", 0.5),
    exposure: num("--scene-exposure", 1),
    bloomStrength: num("--scene-bloom-strength", 0.8),
    bloomRadius: num("--scene-bloom-radius", 0.5),
    bloomThreshold: num("--scene-bloom-threshold", 0.9),
    bokeh: color("--scene-bokeh"),
    bokehPower: num("--scene-bokeh-power", 0),
    gloss: num("--cube-gloss", 0.4),
    glowPower: num("--scene-glow-power", 0.55),
    haloPower: num("--scene-halo-power", 0),
    haloOver: raw("--scene-halo-blend") === "over",
    poolPower: num("--scene-pool-power", 1),
    sparkPower: num("--scene-spark-power", 2.4),
    beyond: color("--cube-beyond", "#ffffff"),
    cubes,
    fontDisplay: raw("--font-display") || "sans-serif",
  };
}

/** The ramp step of a value: 2 is 0, 4 is 1, … 4096 is 11; larger values stay on the last step. */
export function stepOf(value) {
  return Math.max(0, Math.min(STEPS - 1, Math.round(Math.log2(value)) - 1));
}
