// The sun and the sky light. The sun's shadow camera is fitted around the explorer's patch of the planet, so its
// shadows stay crisp and lengthen and swing as the sun goes down; from orbit it widens to hold the whole planet.
import * as THREE from "three";

const smooth = THREE.MathUtils.smoothstep;

export function buildLights(settings) {
  const hemi = new THREE.HemisphereLight(0xffffff, 0x444444, 1);
  const sun = new THREE.DirectionalLight(0xffffff, 2.4);
  const target = new THREE.Object3D();
  sun.target = target;
  const half = 21;
  Object.assign(sun.shadow.camera, { left: -half, right: half, top: half, bottom: -half, near: 1, far: 90 });
  sun.shadow.bias = -0.0006;
  sun.shadow.normalBias = 0.05;
  sun.shadow.radius = 2.5;

  function setShadowSize(size) {
    sun.castShadow = size > 0;
    if (size > 0 && sun.shadow.mapSize.x !== size) {
      sun.shadow.mapSize.set(size, size);
      if (sun.shadow.map) {
        sun.shadow.map.dispose();
        sun.shadow.map = null;
      }
    }
    sun.shadow.normalBias = size >= 2048 ? 0.04 : 0.07;
  }
  setShadowSize(settings.shadowSize);

  const tmp = new THREE.Color();
  const cool = new THREE.Color();

  const center = new THREE.Vector3();

  // orbit: 0 to 1, how much of the title's orbit shot is on screen; evening: 0 at noon to 1 at sunset, as the title
  // sees the theme. At dusk from orbit the low sun is strong, golden, and from the side, and the sky light is dim
  // and takes the dusk sky's color, so the lit half of the planet glows warm and the night half reads cool.
  function update({ focus, up, sunDir, e, sky, orbit, evening }) {
    center.copy(focus).multiplyScalar(1 - orbit);
    const size = THREE.MathUtils.lerp(half, 27, orbit);
    const cam = sun.shadow.camera;
    if (Math.abs(cam.right - size) > 0.01) {
      Object.assign(cam, { left: -size, right: size, top: size, bottom: -size });
      cam.updateProjectionMatrix();
    }
    target.position.copy(center);
    target.updateMatrixWorld();
    sun.position.copy(center).addScaledVector(sunDir, 45);
    const strength = smooth(e, -0.06, 0.16);
    const golden = orbit * evening;
    sun.intensity = THREE.MathUtils.lerp(2.5 * strength, 4.4, golden);
    sun.color.copy(sky.sunColor).lerp(tmp.setRGB(1, 1, 1), golden * 0.2);
    hemi.position.copy(up);
    hemi.color.copy(sky.zenith).lerp(tmp.setRGB(1, 1, 1), 0.35 * (1 - sky.night)).lerp(cool.copy(sky.zenith).multiplyScalar(2.1), golden * 0.9);
    hemi.groundColor.copy(sky.horizon).multiplyScalar(0.55).lerp(cool.copy(sky.zenith).multiplyScalar(0.5), golden);
    hemi.intensity = THREE.MathUtils.lerp(1.15, 1.6, sky.night) * (0.75 + 0.25 * strength) * (1 - golden * 0.38);
  }

  return { group: [hemi, sun, target], sun, setShadowSize, update };
}
