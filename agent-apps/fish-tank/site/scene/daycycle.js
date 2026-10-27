// The day in the tank: phase 0 is noon, 0.25 dusk, 0.5 midnight, 0.75 dawn. The palette comes from the theme's
// --scene-* tokens, so each theme lights its own noon, dusk, and night.
import * as THREE from "three";

const NAMES = [
  "noon-water", "noon-deep", "noon-key", "dusk-water", "dusk-deep", "dusk-key", "night-water", "night-deep",
  "night-key", "lamp", "sand", "sand2", "rock", "plant", "plant-tip", "glow", "ray", "food", "pearl",
];

export function readPalette() {
  const css = getComputedStyle(document.documentElement);
  const out = {};
  for (const name of NAMES) {
    const raw = css.getPropertyValue(`--scene-${name}`).trim();
    out[name.replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = new THREE.Color(raw || "#808080");
  }
  return out;
}

export function phaseAt(now, anchor, cycleMinutes) {
  const cycle = cycleMinutes * 60000;
  const p = ((now - anchor) / cycle) % 1;
  return p < 0 ? p + 1 : p;
}

export function labelFor(phase) {
  if (phase < 0.125 || phase >= 0.875) return phase < 0.06 || phase > 0.94 ? "Noon" : phase < 0.5 ? "Afternoon" : "Morning";
  if (phase < 0.32) return "Dusk";
  if (phase < 0.68) return "Night";
  return "Dawn";
}

const tmp = new THREE.Color();

// Everything the scene needs from the hour, written into `mood` without allocating.
export function moodAt(phase, pal, mood) {
  const day = Math.cos(phase * Math.PI * 2) * 0.5 + 0.5; // 1 at noon, 0 at midnight
  const golden = Math.pow(Math.abs(Math.sin(phase * Math.PI * 2)), 3); // peaks at dusk and dawn
  const goldenWeight = golden * 0.9;
  const mix3 = (out, noon, dusk, night) => {
    out.copy(night).lerp(noon, day);
    out.lerp(dusk, goldenWeight);
    return out;
  };
  mix3(mood.water, pal.noonWater, pal.duskWater, pal.nightWater);
  mix3(mood.deep, pal.noonDeep, pal.duskDeep, pal.nightDeep);
  mix3(mood.key, pal.noonKey, pal.duskKey, pal.nightKey);
  mood.day = day;
  mood.golden = golden;
  mood.lamp = THREE.MathUtils.smoothstep(0.42, 0.12, day);
  mood.keyIntensity = 0.35 + 2.4 * day + golden * 0.5;
  mood.ambient = 0.18 + 0.75 * day;
  mood.rays = 0.12 + 0.88 * Math.pow(day, 1.4) + golden * 0.25;
  mood.caustic = 0.15 + 1.0 * Math.pow(day, 1.2) + golden * 0.3;
  mood.slow = 1 - 0.45 * (1 - day) * (1 - golden * 0.5);
  mood.glow = 0.55 + 0.45 * (1 - day);
  // the tank lamp at night: a cool light from above that gives the caustics something to throw
  tmp.copy(pal.lamp);
  mood.key.lerp(tmp, mood.lamp * 0.7);
  mood.keyIntensity += mood.lamp * 0.55;
  mood.caustic += mood.lamp * 0.15;
  return mood;
}

export function createMood() {
  return {
    water: new THREE.Color(), deep: new THREE.Color(), key: new THREE.Color(),
    day: 1, golden: 0, lamp: 0, keyIntensity: 1, ambient: 1, rays: 1, caustic: 1, slow: 1, glow: 1,
  };
}
