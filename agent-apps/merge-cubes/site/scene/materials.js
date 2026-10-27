// One named export per look. Every color comes from the theme's tokens (tokens.js).
import * as THREE from "three";

/**
 * A cube: candy-glossy with a clear coat, glowing from inside by its step on the ramp. It sits in the see-through
 * pass (at full opacity) so it can be drawn after the glows round it and fade without a second shader.
 */
export function cubeMaterial(tokens, step) {
  return tuneCube(new THREE.MeshPhysicalMaterial({ metalness: 0, clearcoat: 0.7, clearcoatRoughness: 0.18, transparent: true }), tokens, step);
}

/** Sets a cube's material to a step of the ramp; every step shares one shader, so a cube can be dressed as any value. */
export function tuneCube(mat, tokens, step) {
  const look = tokens.cubes[step];
  mat.color.copy(look.color);
  mat.roughness = THREE.MathUtils.clamp(tokens.gloss + (step < 2 ? 0.22 : 0) - step * 0.012, 0.12, 0.85);
  mat.clearcoat = step < 2 ? 0.25 : 0.7;
  mat.emissive.copy(look.heat);
  mat.emissiveIntensity = tokens.glowPower * look.glow;
  return mat;
}

/** The face printed on a cube's top: flat ink in the theme's exact color, so the number reads the same under any light. */
export function labelMaterial(map) {
  return new THREE.MeshBasicMaterial({
    map,
    transparent: true,
    toneMapped: false,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    polygonOffsetUnits: -2,
  });
}

/** The tray: smoked glass, near black or pale pearl, with a mirror clear coat that catches the room. */
export function glassTray(tokens) {
  return new THREE.MeshPhysicalMaterial({
    color: tokens.tray.clone(),
    roughness: 0.16,
    metalness: 0.1,
    clearcoat: 1,
    clearcoatRoughness: 0.05,
    reflectivity: 0.6,
  });
}

/** The sockets etched into the tray top, drawn into a texture. */
export function socketSheet(tokens, map) {
  return new THREE.MeshPhysicalMaterial({
    map,
    transparent: true,
    roughness: 0.22,
    metalness: 0,
    clearcoat: 1,
    clearcoatRoughness: 0.08,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -1,
    polygonOffsetUnits: -1,
  });
}

/** A light line that glows past the bloom threshold: the tray's inlay and the pedestal's band. */
export function lightLine(color, power) {
  return new THREE.MeshBasicMaterial({ color: color.clone().multiplyScalar(power) });
}

/** The pedestal: satin metal, lit from its band down. */
export function pedestalMetal(tokens, glowMap) {
  return new THREE.MeshStandardMaterial({
    color: tokens.pedestal.clone(),
    roughness: 0.42,
    metalness: 0.55,
    emissive: tokens.band.clone(),
    emissiveMap: glowMap,
    emissiveIntensity: 0.55 * tokens.bandGlow,
  });
}

/** The stage floor: the theme's floor with its pool of light painted in, unlit so it meets the page's own color. */
export function floorStone(map) {
  return new THREE.MeshBasicMaterial({ map, toneMapped: false });
}

/** The soft shade the pedestal leaves where it stands on the floor. */
export function contactShade(map) {
  return new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false, toneMapped: false });
}

/** The glow round a high cube, added onto the tray and the air round it. */
export function haloMaterial(map) {
  return new THREE.SpriteMaterial({ map, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false });
}

/** The pool of a lit cube's light spilled on the tray round its foot. */
export function poolMaterial(map) {
  return new THREE.MeshBasicMaterial({ map, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false });
}

/** The sparks that fly off a merge. */
export function sparkMaterial() {
  return new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, depthWrite: false, toneMapped: false });
}
