// Graze sparks: 2,048 streaks in a ring buffer. A burst writes origin, velocity, birth, life, and color once; the
// vertex shader moves and fades every spark from one time uniform.
import * as THREE from "three";
import { sparkMaterial } from "./materials.js";

export const SPARKS = 2048;

export function createSparks(mode) {
  const base = new THREE.PlaneGeometry(1, 1);
  const geo = new THREE.InstancedBufferGeometry();
  geo.index = base.index;
  geo.setAttribute("position", base.getAttribute("position"));
  const motion = new THREE.InstancedBufferAttribute(new Float32Array(SPARKS * 4), 4);
  const life = new THREE.InstancedBufferAttribute(new Float32Array(SPARKS * 2).fill(-100), 2);
  const color = new THREE.InstancedBufferAttribute(new Float32Array(SPARKS * 3), 3);
  for (const a of [motion, life, color]) a.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute("aMotion", motion);
  geo.setAttribute("aLife", life);
  geo.setAttribute("aColor", color);
  geo.instanceCount = SPARKS;
  const mesh = new THREE.Mesh(geo, sparkMaterial(mode));
  mesh.frustumCulled = false;
  mesh.renderOrder = 4;
  let head = 0;
  let lo = Infinity;
  let hi = -1;
  let time = 0;

  return {
    mesh,
    /** count sparks from (x, y) at speeds around `speed`, centered on `heading` with `spread` radians either side. */
    burst(x, y, count, speed, c1, c2, rng, heading = 0, spread = Math.PI) {
      for (let k = 0; k < count; k++) {
        const i = head;
        head = (head + 1) % SPARKS;
        const a = heading + rng.range(-spread, spread);
        const s = speed * rng.range(0.45, 1.25);
        motion.array.set([x, y, Math.cos(a) * s, Math.sin(a) * s], i * 4);
        life.array.set([time, rng.range(0.35, 0.75) * (speed > 40 ? 1.8 : 1)], i * 2);
        const c = rng.next() < 0.5 ? c1 : c2;
        color.array.set([c.r, c.g, c.b], i * 3);
        if (i < lo) lo = i;
        if (i > hi) hi = i;
      }
    },
    update(t) {
      time = t;
      mesh.material.uniforms.uTime.value = t;
      if (hi < 0) return;
      for (const [a, size] of [[motion, 4], [life, 2], [color, 3]]) {
        a.clearUpdateRanges();
        a.addUpdateRange(lo * size, (hi - lo + 1) * size);
        a.needsUpdate = true;
      }
      lo = Infinity;
      hi = -1;
    },
    setLook(mode) {
      const t = mesh.material.uniforms.uTime.value;
      mesh.material.dispose();
      mesh.material = sparkMaterial(mode);
      mesh.material.uniforms.uTime.value = t;
    },
  };
}
