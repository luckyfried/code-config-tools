// Small effects from fixed pools: dust puffs at the feet, a shockwave ring and a burst of sparks on a collect.
import * as THREE from "three";
import { gemMaterial, glowMaterial } from "./materials.js";

const UP = new THREE.Vector3(0, 1, 0);

function pool(geometry, material, size) {
  const mesh = new THREE.InstancedMesh(geometry, material, size);
  mesh.frustumCulled = false;
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  const zero = new THREE.Matrix4().makeScale(0, 0, 0);
  for (let i = 0; i < size; i++) mesh.setMatrixAt(i, zero);
  const slots = Array.from({ length: size }, () => ({
    life: 0, max: 1, p: new THREE.Vector3(), v: new THREE.Vector3(), q: new THREE.Quaternion(), s: 1,
  }));
  return { mesh, slots, next: 0 };
}

export function buildFx(colors) {
  const group = new THREE.Group();
  group.name = "fx";
  const dustMat = new THREE.MeshLambertMaterial({ color: colors.worldDust });
  const dust = pool(new THREE.IcosahedronGeometry(0.16, 0), dustMat, 48);
  const sparks = pool(new THREE.OctahedronGeometry(0.11, 0), gemMaterial(colors.crystal), 64);
  group.add(dust.mesh, sparks.mesh);

  const ringGeo = new THREE.RingGeometry(0.82, 1, 48);
  ringGeo.rotateX(-Math.PI / 2);
  const rings = Array.from({ length: 3 }, () => {
    const mesh = new THREE.Mesh(ringGeo, glowMaterial(colors.crystal));
    mesh.visible = false;
    mesh.renderOrder = 7;
    group.add(mesh);
    return { mesh, life: 0 };
  });
  let ringNext = 0;

  const m = new THREE.Matrix4();
  const s = new THREE.Vector3();

  function emit(p, at, up, velocity, max, scale) {
    const slot = p.slots[p.next];
    p.next = (p.next + 1) % p.slots.length;
    slot.life = max;
    slot.max = max;
    slot.p.copy(at);
    slot.v.copy(velocity);
    slot.q.setFromUnitVectors(UP, up);
    slot.s = scale;
  }

  function step(p, dt, drag, gravityUp) {
    for (let i = 0; i < p.slots.length; i++) {
      const slot = p.slots[i];
      if (slot.life <= 0) continue;
      slot.life -= dt;
      if (slot.life <= 0) {
        m.makeScale(0, 0, 0);
        p.mesh.setMatrixAt(i, m);
        continue;
      }
      slot.v.multiplyScalar(Math.exp(-drag * dt));
      if (gravityUp) slot.v.addScaledVector(gravityUp, -4 * dt);
      slot.p.addScaledVector(slot.v, dt);
      const k = slot.life / slot.max;
      s.setScalar(slot.s * Math.sin(Math.PI * Math.min(1, (1 - k) * 1.4 + 0.15)) * (0.4 + 0.6 * k));
      m.compose(slot.p, slot.q, s);
      p.mesh.setMatrixAt(i, m);
    }
    p.mesh.instanceMatrix.needsUpdate = true;
  }

  const tmp = new THREE.Vector3();
  const side = new THREE.Vector3();

  return {
    group,
    // A puff of dust at the feet: a few motes thrown outward along the ground.
    puff(at, up, count, strength) {
      side.set(1, 0, 0);
      if (Math.abs(up.x) > 0.9) side.set(0, 0, 1);
      side.cross(up).normalize();
      for (let i = 0; i < count; i++) {
        const a = Math.random() * Math.PI * 2;
        tmp.copy(side).applyAxisAngle(up, a).multiplyScalar(strength * (0.6 + Math.random() * 0.8)).addScaledVector(up, 0.4 + Math.random() * 0.6);
        emit(dust, at, up, tmp, 0.45 + Math.random() * 0.3, 0.6 + Math.random() * 0.7);
      }
    },
    burst(at, up) {
      for (let i = 0; i < 26; i++) {
        tmp.randomDirection().addScaledVector(up, 1.1).normalize().multiplyScalar(3 + Math.random() * 4);
        emit(sparks, at, up, tmp, 0.7 + Math.random() * 0.5, 0.7 + Math.random() * 0.8);
      }
      const ring = rings[ringNext];
      ringNext = (ringNext + 1) % rings.length;
      ring.life = 0.9;
      ring.mesh.visible = true;
      ring.mesh.position.copy(at).addScaledVector(up, -0.85);
      ring.mesh.quaternion.setFromUnitVectors(UP, up);
    },
    update(dt, localUp) {
      step(dust, dt, 3.5, null);
      step(sparks, dt, 1.6, localUp);
      for (const ring of rings) {
        if (ring.life <= 0) continue;
        ring.life -= dt;
        const k = 1 - ring.life / 0.9;
        ring.mesh.scale.setScalar(0.6 + k * 7);
        ring.mesh.material.opacity = 0.75 * (1 - k) * (1 - k);
        if (ring.life <= 0) ring.mesh.visible = false;
      }
    },
  };
}
