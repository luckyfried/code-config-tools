// Deliveries: a pickup on a marked roof, then a drop at a lit balcony across town, then the next pickup.
import * as THREE from "three";
import { PITCH } from "./gen.js";

const REACH = 3.4;

export function createDispatch(plan, rng) {
  function pickupTask(pad, approach = null) {
    return {
      kind: "pickup",
      name: pad.name,
      base: new THREE.Vector3(pad.x, pad.y, pad.z),
      point: new THREE.Vector3(pad.x, pad.y + 1.7, pad.z),
      approach,
      nx: 0,
      nz: 0,
    };
  }

  function pickupNear(from, min, max) {
    const pool = plan.pads.filter((p) => {
      const d = Math.hypot(p.x - from.x, p.z - from.z);
      return d >= min && d <= max;
    });
    const pad = pool.length ? rng.pick(pool) : nearest(plan.pads, from);
    return pickupTask(pad);
  }

  function dropFrom(from, min, max) {
    const pool = plan.balconies.filter((b) => {
      const d = Math.hypot(b.x - from.x, b.z - from.z);
      return d >= min && d <= max;
    });
    const b = pool.length ? rng.pick(pool) : nearest(plan.balconies, from);
    const point = new THREE.Vector3(b.x + b.nx * 2.8, b.y + 1.5, b.z + b.nz * 2.8);
    return {
      kind: "drop",
      name: `${b.name}, floor ${b.floor}`,
      base: new THREE.Vector3(b.x + b.nx * 0.9, b.y + 1.1, b.z + b.nz * 0.9),
      point,
      approach: new THREE.Vector3(b.x + b.nx * 9, b.y + 1.5, b.z + b.nz * 9),
      nx: b.nx,
      nz: b.nz,
    };
  }

  return {
    // The opening run: a low roof that fronts a street, reached by flying up that street between the towers.
    opening() {
      let best = null;
      for (const pad of plan.pads) {
        if (pad.y < 14 || pad.y > 40) continue;
        const sx = Math.round((pad.x + plan.halfX) / PITCH) * PITCH - plan.halfX;
        const sz = Math.round((pad.z + plan.halfZ) / PITCH) * PITCH - plan.halfZ;
        const gx = Math.abs(pad.x - sx) - pad.w / 2;
        const gz = Math.abs(pad.z - sz) - pad.d / 2;
        const alongZ = gx < gz;
        if (Math.min(gx, gz) > 9) continue;
        const score = Math.hypot(pad.x - plan.downtown.x, pad.z - plan.downtown.z) * 0.6 + Math.abs(pad.y - 24) * 2;
        if (!best || score < best.score) best = { pad, sx, sz, alongZ, score };
      }
      if (!best) return null;
      const { pad, sx, sz, alongZ } = best;
      const y = pad.y + 5;
      // Fly in from the side of the pad nearer the middle of town, so the street ahead is lined with towers.
      const toward = alongZ ? -Math.sign(pad.z - plan.downtown.z) || 1 : -Math.sign(pad.x - plan.downtown.x) || 1;
      const approach = alongZ ? new THREE.Vector3(sx, y, pad.z) : new THREE.Vector3(pad.x, y, sz);
      const start = alongZ ? new THREE.Vector3(sx, y - 2, pad.z + toward * 85) : new THREE.Vector3(pad.x + toward * 85, y - 2, sz);
      return { task: pickupTask(pad, approach), start };
    },
    firstPickup(from, near = false) {
      return near ? pickupNear(from, 45, 90) : pickupNear(from, 70, 170);
    },
    nextDrop(from, near = false) {
      return near ? dropFrom(from, 70, 130) : dropFrom(from, 120, 300);
    },
    nextPickup(from) {
      return pickupNear(from, 60, 170);
    },
    reached(task, pos) {
      return Math.hypot(task.point.x - pos.x, task.point.z - pos.z) < REACH && Math.abs(task.point.y - pos.y) < REACH;
    },
  };
}

function nearest(list, from) {
  let best = list[0];
  let bd = Infinity;
  for (const p of list) {
    const d = Math.hypot(p.x - from.x, p.z - from.z);
    if (d < bd) {
      bd = d;
      best = p;
    }
  }
  return best;
}
