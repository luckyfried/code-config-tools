// The light: a sky and ground fill, and a low sun from the west-southwest under the storm that casts the shadows. The shadow
// box follows the storm, so the town around it is always shaded.
import * as THREE from "three";

export function createLights({ tokens, shadowSize }) {
  const group = new THREE.Group();
  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1);
  const sun = new THREE.DirectionalLight(0xffffff, 2);
  sun.castShadow = shadowSize > 0;
  if (shadowSize > 0) {
    sun.shadow.mapSize.set(shadowSize, shadowSize);
    const c = sun.shadow.camera;
    c.left = -55;
    c.right = 55;
    c.top = 55;
    c.bottom = -55;
    c.near = 10;
    c.far = 260;
    sun.shadow.bias = -0.0006;
    sun.shadow.normalBias = 0.04;
  }
  group.add(hemi, sun, sun.target);
  const dir = new THREE.Vector3();
  const api = {
    group,
    hemi,
    sun,
    dir,
    applyTokens(t) {
      hemi.color.copy(t.colors.hemiSky);
      hemi.groundColor.copy(t.colors.hemiGround);
      hemi.intensity = t.numbers.hemiIntensity;
      sun.color.copy(t.colors.sun);
      sun.intensity = t.numbers.sunIntensity;
      const e = THREE.MathUtils.degToRad(t.numbers.sunElevation || 30);
      const az = THREE.MathUtils.degToRad(-62);
      dir.set(Math.cos(e) * Math.sin(az), Math.sin(e), Math.cos(e) * Math.cos(az)).normalize();
    },
    follow(focus) {
      sun.target.position.set(focus.x, 0, focus.z - 10);
      sun.position.copy(sun.target.position).addScaledVector(dir, 140);
    },
    lighting() {
      return {
        sunDir: dir,
        sunColor: sun.color,
        sunI: sun.intensity,
        skyColor: hemi.color,
        groundColor: hemi.groundColor,
        hemiI: hemi.intensity,
      };
    },
  };
  api.applyTokens(tokens);
  return api;
}
