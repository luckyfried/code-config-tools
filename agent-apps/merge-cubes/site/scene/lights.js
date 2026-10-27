// Key, fill, and rim, plus the room's reflections, and a small pool of lights a merge borrows to light its
// neighbors for a moment.
import * as THREE from "three";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

export function createLights(scene, renderer, tier) {
  const pmrem = new THREE.PMREMGenerator(renderer);
  const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  pmrem.dispose();
  scene.environment = env;

  const hemi = new THREE.HemisphereLight(0xffffff, 0x000000, 1);
  scene.add(hemi);

  const key = new THREE.DirectionalLight(0xffffff, 2);
  key.position.set(-4.5, 10, 6.5);
  scene.add(key);
  scene.add(key.target);

  const back = new THREE.DirectionalLight(0xffffff, 1);
  back.position.set(3, 4, -9);
  scene.add(back);

  const flashes = [];
  for (let i = 0; i < 3; i += 1) {
    const p = new THREE.PointLight(0xffffff, 0, 4.8, 2);
    p.position.set(0, 0.9, 0);
    scene.add(p);
    flashes.push({ light: p, life: 0, power: 0 });
  }
  let next = 0;
  let base = { key: 2, hemi: 1, back: 1 };
  let dim = 0;

  return {
    apply(tokens) {
      hemi.color.copy(tokens.fillSky);
      hemi.groundColor.copy(tokens.fillGround);
      key.color.copy(tokens.key);
      back.color.copy(tokens.back);
      base = { key: tokens.keyPower, hemi: tokens.fillPower, back: tokens.backPower, env: tokens.envPower };
      scene.environmentIntensity = tokens.envPower;
    },
    /** Lights a merge's neighbors in its own color for a moment. */
    flash(x, z, color, power) {
      const f = flashes[next];
      next = (next + 1) % flashes.length;
      f.light.position.set(x, 1.7, z);
      f.light.color.copy(color);
      f.power = power;
      f.life = 1;
    },
    setDim(value) {
      dim = value;
    },
    update(dt) {
      const k = 1 - 0.7 * dim;
      key.intensity = base.key * k;
      hemi.intensity = base.hemi * (1 - 0.6 * dim);
      back.intensity = base.back * k;
      scene.environmentIntensity = (base.env ?? 0.5) * (1 - 0.65 * dim);
      for (const f of flashes) {
        if (f.life <= 0) {
          f.light.intensity = 0;
          continue;
        }
        f.life = Math.max(0, f.life - dt / 0.42);
        f.light.intensity = f.power * f.life * f.life;
      }
    },
  };
}
