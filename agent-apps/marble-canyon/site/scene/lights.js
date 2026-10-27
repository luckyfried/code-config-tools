// One low sun that throws long shadows near the marble, and a sky-and-ground fill.
import { DirectionalLight, HemisphereLight, Object3D } from "three";

export function createLights(tokens, tier) {
  const hemi = new HemisphereLight(tokens.hemiSky, tokens.hemiGround, tokens.hemiIntensity);
  const sun = new DirectionalLight(tokens.sun, tokens.sunIntensity);
  const target = new Object3D();
  sun.target = target;
  sun.castShadow = tier.shadows;
  if (tier.shadows) {
    sun.shadow.mapSize.set(tier.shadowSize, tier.shadowSize);
    const cam = sun.shadow.camera;
    cam.left = -22;
    cam.right = 22;
    cam.top = 22;
    cam.bottom = -22;
    cam.near = 1;
    cam.far = 240;
    sun.shadow.bias = -0.0004;
    sun.shadow.normalBias = 0.03;
  }
  const dir = tokens.sunDir.clone();
  return {
    hemi,
    sun,
    target,
    follow(point) {
      target.position.copy(point);
      sun.position.copy(point).addScaledVector(dir, 110);
    },
    apply(t) {
      hemi.color.copy(t.hemiSky);
      hemi.groundColor.copy(t.hemiGround);
      hemi.intensity = t.hemiIntensity;
      sun.color.copy(t.sun);
      sun.intensity = t.sunIntensity;
      dir.copy(t.sunDir);
    },
  };
}
