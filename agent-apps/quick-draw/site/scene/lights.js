// One key light from the sun (or moon) throwing long shadows up the street, a sky-and-dust hemisphere fill,
// and a muzzle-flash light that stays in the scene at zero so the shaders never recompile mid-duel.
import * as THREE from "three";
import { sunDirection } from "./sky.js";

export function createLights(tokens, tier) {
  const group = new THREE.Group();

  const sun = new THREE.DirectionalLight(tokens.light, tokens.lightIntensity);
  sun.castShadow = true;
  sun.shadow.mapSize.set(tier.shadowSize, tier.shadowSize);
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.04;
  sun.shadow.radius = 3;
  const cam = sun.shadow.camera;
  cam.near = 1;
  cam.far = 260;
  group.add(sun, sun.target);

  const hemi = new THREE.HemisphereLight(tokens.ambientSky, tokens.ambientGround, tokens.ambientIntensity);
  group.add(hemi);

  const flash = new THREE.PointLight(0xffd29a, 0, 9, 1.6);
  group.add(flash);

  const focus = new THREE.Vector3(0, 0, -6);

  function apply(t) {
    sun.color.copy(t.light);
    sun.intensity = t.lightIntensity;
    hemi.color.copy(t.ambientSky);
    hemi.groundColor.copy(t.ambientGround);
    hemi.intensity = t.ambientIntensity;
    const dir = sunDirection(t);
    // Low sun: the shadow frustum stretches along the street; high sun: it tightens around the duel.
    const low = 1 - THREE.MathUtils.smoothstep(t.sunElevation, 8, 40);
    sun.position.copy(focus).addScaledVector(dir, 120);
    sun.target.position.copy(focus);
    const half = 22 + low * 6;
    cam.left = -half;
    cam.right = half;
    cam.top = THREE.MathUtils.lerp(32, 18, low);
    cam.bottom = -cam.top;
    cam.updateProjectionMatrix();
  }
  apply(tokens);

  return { group, sun, hemi, flash, apply };
}
