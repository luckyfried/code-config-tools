// Four thousand stars on two parallax layers between the play plane and the backdrop.
import * as THREE from "three";
import { starMaterial } from "./materials.js";
import { createRng } from "../game/rng.js";

const LAYERS = [
  { count: 2600, z: -150, speed: 0.012, size: 2.2 },
  { count: 1400, z: -34, speed: 0.03, size: 3.0 },
];

export function createStars(mode, tokens) {
  const rng = createRng(4242);
  const group = new THREE.Group();
  const layers = LAYERS.map((layer) => {
    const pos = new Float32Array(layer.count * 3);
    const seed = new Float32Array(layer.count);
    for (let i = 0; i < layer.count; i++) {
      pos[i * 3] = rng.range(-1, 1);
      pos[i * 3 + 1] = rng.range(-1, 1);
      pos[i * 3 + 2] = layer.z;
      seed[i] = rng.next();
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("aSeed", new THREE.BufferAttribute(seed, 1));
    const points = new THREE.Points(geo, starMaterial(mode, tokens.star, layer.speed, layer.size));
    points.frustumCulled = false;
    points.renderOrder = -9;
    group.add(points);
    return { ...layer, points };
  });
  return {
    group,
    fit(W, H, distance, ratio) {
      for (const l of layers) {
        const grow = ((distance - l.z) / distance) * 1.35;
        l.points.material.uniforms.uExtent.value.set(W * grow, H * grow);
        l.points.material.uniforms.uRatio.value = ratio;
      }
    },
    update(time) {
      for (const l of layers) l.points.material.uniforms.uTime.value = time;
    },
    setLook(mode, tokens) {
      for (const l of layers) {
        const old = l.points.material;
        l.points.material = starMaterial(mode, tokens.star, l.speed, l.size);
        l.points.material.uniforms.uExtent.value.copy(old.uniforms.uExtent.value);
        l.points.material.uniforms.uRatio.value = old.uniforms.uRatio.value;
        old.dispose();
      }
    },
  };
}
