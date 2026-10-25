// The crystals: a glowing gem with a ring of shards, a pool of light on the ground, and a tall beam that can be
// seen from far across the planet. A found crystal spins up, lifts, and pops; its beam fades out.
import * as THREE from "three";
import { RADIUS } from "../game/generation.js";
import { beamMaterial, gemMaterial, glowMaterial } from "./materials.js";

const UP = new THREE.Vector3(0, 1, 0);

export function buildCrystals(terrain, dirs, colors) {
  const group = new THREE.Group();
  group.name = "crystals";
  const gemGeo = new THREE.OctahedronGeometry(0.42, 0);
  gemGeo.scale(1, 1.75, 1);
  const shardGeo = new THREE.OctahedronGeometry(0.16, 0);
  shardGeo.scale(1, 2.2, 1);
  const beamGeo = new THREE.CylinderGeometry(0.42, 0.75, 46, 20, 1, true);
  beamGeo.translate(0, 23, 0);
  const poolGeo = new THREE.CircleGeometry(1.7, 32);
  poolGeo.rotateX(-Math.PI / 2);

  const gemMat = gemMaterial(colors.crystal);
  const poolMat = glowMaterial(colors.crystal);

  const items = dirs.map((d, i) => {
    const dir = new THREE.Vector3(...d).normalize();
    const ground = RADIUS + Math.max(terrain.height(dir.x, dir.y, dir.z), 0);
    const root = new THREE.Group();
    root.position.copy(dir).multiplyScalar(ground);
    root.quaternion.setFromUnitVectors(UP, dir);

    const spin = new THREE.Group();
    spin.position.y = 1.05;
    const gem = new THREE.Mesh(gemGeo, gemMat);
    spin.add(gem);
    const shards = new THREE.Group();
    for (let k = 0; k < 5; k++) {
      const a = (k / 5) * Math.PI * 2;
      const s = new THREE.Mesh(shardGeo, gemMat);
      s.position.set(Math.cos(a) * 0.62, -0.55 + (k % 2) * 0.12, Math.sin(a) * 0.62);
      s.rotation.set(Math.sin(a) * 0.5, 0, -Math.cos(a) * 0.5);
      shards.add(s);
    }
    const beam = new THREE.Mesh(beamGeo, beamMaterial(colors.crystal));
    beam.frustumCulled = false;
    beam.renderOrder = 6;
    const pool = new THREE.Mesh(poolGeo, poolMat);
    pool.position.y = 0.06;
    pool.renderOrder = 4;
    root.add(spin, shards, beam, pool);
    group.add(root);
    return { index: i, dir, root, spin, shards, beam, pool, found: false, t: 0, phase: i * 1.3 };
  });

  return {
    group,
    items,
    collect(item) {
      item.found = true;
      item.t = 0;
    },
    update(dt, time, reduced) {
      for (const item of items) {
        if (!item.found) {
          const bob = reduced ? 0 : Math.sin(time * 2 + item.phase) * 0.12;
          item.spin.position.y = 1.05 + bob;
          item.spin.rotation.y = time * 0.9 + item.phase;
          item.shards.rotation.y = -time * 0.3;
          continue;
        }
        if (!item.root.visible) continue;
        item.t += dt;
        const t = item.t;
        const pop = Math.min(t / 0.7, 1);
        item.spin.rotation.y += dt * (6 + 20 * pop);
        item.spin.position.y = 1.05 + pop * pop * 1.8;
        const s = pop < 0.35 ? 1 + pop * 1.4 : Math.max(0, 1.49 * (1 - (pop - 0.35) / 0.65));
        item.spin.scale.setScalar(s);
        item.shards.scale.setScalar(Math.max(0, 1 - pop * 1.6));
        item.beam.material.uniforms.uFade.value = Math.max(0, 1 - t / 1.2);
        item.pool.scale.setScalar(1 + t * 1.5);
        item.pool.visible = t < 0.7;
        if (t > 1.25) item.root.visible = false;
      }
    },
    reset() {
      for (const item of items) {
        item.found = false;
        item.t = 0;
        item.root.visible = true;
        item.spin.scale.setScalar(1);
        item.shards.scale.setScalar(1);
        item.pool.scale.setScalar(1);
        item.pool.visible = true;
        item.beam.material.uniforms.uFade.value = 1;
      }
    },
  };
}
