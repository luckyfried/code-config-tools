// The world's colors come from the theme tokens, so a theme or a color scheme recolors the city.
import * as THREE from "three";

const COLOR_TOKENS = {
  sign1: "--scene-sign-1", sign2: "--scene-sign-2", sign3: "--scene-sign-3",
  skyTop: "--scene-sky-top", skyHorizon: "--scene-sky-horizon", cloud: "--scene-cloud",
  fogNear: "--scene-fog-near", fogFar: "--scene-fog-far",
  building: "--scene-building", buildingLight: "--scene-building-light", roof: "--scene-roof",
  windowWarm: "--scene-window-warm", windowCool: "--scene-window-cool",
  street: "--scene-street", lamp: "--scene-lamp", rain: "--scene-rain", route: "--scene-route",
  pickup: "--scene-pickup", drop: "--scene-drop", flash: "--scene-flash",
  droneBody: "--scene-drone-body", droneTrim: "--scene-drone-trim", danger: "--color-danger",
};
const NUMBER_TOKENS = {
  fogDensity: "--scene-fog-density", windowLit: "--scene-window-lit", exposure: "--scene-exposure",
  bloom: "--scene-bloom", glow: "--scene-glow", signHalo: "--scene-sign-halo",
};

export function readPalette() {
  const css = getComputedStyle(document.documentElement);
  const palette = {};
  for (const [key, name] of Object.entries(COLOR_TOKENS)) {
    const value = css.getPropertyValue(name).trim() || "#808080";
    palette[key] = new THREE.Color(value);
  }
  for (const [key, name] of Object.entries(NUMBER_TOKENS)) {
    palette[key] = parseFloat(css.getPropertyValue(name)) || 0;
  }
  palette.light = css.getPropertyValue("color-scheme").trim() === "light";
  return palette;
}

// One set of uniforms every custom shader shares, so a palette change or a thunder flash reaches all of them at once.
export function createShared() {
  return {
    uTime: { value: 0 },
    uFlash: { value: 0 },
    uFogNear: { value: new THREE.Color() },
    uFogFar: { value: new THREE.Color() },
    uFogDensity: { value: 0.005 },
    uSkyTop: { value: new THREE.Color() },
    uSkyHorizon: { value: new THREE.Color() },
    uCloud: { value: new THREE.Color() },
    uFlashColor: { value: new THREE.Color() },
    uGlow: { value: 1 },
  };
}

export function applyPalette(shared, palette) {
  shared.uFogNear.value.copy(palette.fogNear);
  shared.uFogFar.value.copy(palette.fogFar);
  shared.uFogDensity.value = palette.fogDensity;
  shared.uSkyTop.value.copy(palette.skyTop);
  shared.uSkyHorizon.value.copy(palette.skyHorizon);
  shared.uCloud.value.copy(palette.cloud);
  shared.uFlashColor.value.copy(palette.flash);
  shared.uGlow.value = palette.glow;
}

// Warm fog close in, cool fog far out, thicker near the street; mixed in every custom shader.
export const FOG_GLSL = /* glsl */ `
uniform vec3 uFogNear;
uniform vec3 uFogFar;
uniform float uFogDensity;
uniform float uFlash;
uniform vec3 uFlashColor;
float fogAmount(vec3 worldPos, vec3 camPos) {
  float dist = length(worldPos - camPos);
  float heightThin = mix(1.0, 0.55, smoothstep(0.0, 120.0, worldPos.y));
  return 1.0 - exp(-pow(dist * uFogDensity * heightThin, 1.35));
}
vec3 applyFog(vec3 color, vec3 worldPos, vec3 camPos) {
  float dist = length(worldPos - camPos);
  float f = fogAmount(worldPos, camPos);
  vec3 fogColor = mix(uFogNear, uFogFar, smoothstep(30.0, 320.0, dist));
  fogColor += uFlashColor * uFlash * 0.55;
  return mix(color, fogColor, clamp(f, 0.0, 1.0));
}
`;
