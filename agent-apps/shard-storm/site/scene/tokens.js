// Reads the theme's tokens from the page, so one theme file colors the type and the storm alike.
import * as THREE from "three";

export function readTokens(shipColor) {
  const css = getComputedStyle(document.documentElement);
  const color = (name, fallback) => {
    const value = css.getPropertyValue(name).trim();
    const c = new THREE.Color();
    try {
      c.setStyle(value || fallback);
    } catch {
      c.setStyle(fallback);
    }
    return c;
  };
  const day = css.getPropertyValue("--scene-mode").trim() === "day";
  return {
    mode: day ? "day" : "glow",
    bg: color("--scene-bg", "#06041a"),
    bg2: color("--scene-bg-2", "#1a0b3d"),
    grid: color("--scene-grid", "#7a4dff"),
    star: color("--scene-star", "#c9c3ff"),
    a: color("--bullet-a", "#ff2bd6"),
    b: color("--bullet-b", "#22e6ff"),
    c: color("--bullet-c", "#a98bff"),
    spark: color("--spark", "#fff2a8"),
    ship: shipColor ? new THREE.Color().setStyle(shipColor) : color("--ship", "#9dff5c"),
  };
}
