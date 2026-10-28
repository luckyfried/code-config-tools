// The storm on screen: one InstancedMesh of octahedra and a halo layer that shares its matrices and colors. Each frame
// the pool's positions, headings, and spins are written straight into the instance matrices.
import * as THREE from "three";
import { shardMaterial, haloMaterial } from "./materials.js";

const LENGTH = 1.0;
const WIDTH = 0.44;

export function createShards(pool, mode) {
  const capacity = pool.capacity;
  const mesh = new THREE.InstancedMesh(new THREE.OctahedronGeometry(1, 0), shardMaterial(mode), capacity);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(capacity * 3), 3);
  mesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  mesh.renderOrder = 2;
  const halo = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), haloMaterial(mode), capacity);
  halo.instanceMatrix = mesh.instanceMatrix;
  halo.instanceColor = mesh.instanceColor;
  halo.frustumCulled = false;
  halo.renderOrder = 1;
  mesh.count = 0;
  halo.count = 0;

  return {
    mesh,
    halo,
    write() {
      const n = pool.count;
      const e = mesh.instanceMatrix.array;
      const col = mesh.instanceColor.array;
      const { x, y, cos, sin, size, spin, r, g, b } = pool;
      for (let i = 0; i < n; i++) {
        const L = LENGTH * size[i];
        const W = WIDTH * size[i];
        const ch = cos[i];
        const sh = sin[i];
        const cs = Math.cos(spin[i]);
        const ss = Math.sin(spin[i]);
        const o = i * 16;
        e[o] = ch * L;
        e[o + 1] = sh * L;
        e[o + 2] = 0;
        e[o + 3] = 0;
        e[o + 4] = -sh * W * cs;
        e[o + 5] = ch * W * cs;
        e[o + 6] = W * ss;
        e[o + 7] = 0;
        e[o + 8] = sh * W * ss;
        e[o + 9] = -ch * W * ss;
        e[o + 10] = W * cs;
        e[o + 11] = 0;
        e[o + 12] = x[i];
        e[o + 13] = y[i];
        e[o + 14] = 0;
        e[o + 15] = 1;
        const c = i * 3;
        col[c] = r[i];
        col[c + 1] = g[i];
        col[c + 2] = b[i];
      }
      mesh.count = n;
      halo.count = n;
      mesh.instanceMatrix.clearUpdateRanges();
      mesh.instanceMatrix.addUpdateRange(0, Math.max(16, n * 16));
      mesh.instanceMatrix.needsUpdate = true;
      mesh.instanceColor.clearUpdateRanges();
      mesh.instanceColor.addUpdateRange(0, Math.max(3, n * 3));
      mesh.instanceColor.needsUpdate = true;
    },
    setLook(mode) {
      mesh.material.dispose();
      halo.material.dispose();
      mesh.material = shardMaterial(mode);
      halo.material = haloMaterial(mode);
    },
  };
}
