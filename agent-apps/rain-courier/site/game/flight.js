// Flight: thrust along the heading, lift, drag, and the drone's sphere against the buildings' boxes.
// Reports crashes and near misses (within two meters of a wall at speed) as events.
import * as THREE from "three";

export const RADIUS = 0.8;
const THRUST = 26;
const LIFT = 17;
const DRAG = 1.1;
const VDRAG = 2.2;
const TURN = 2.1;
const NEAR = 2.0;
const NEAR_SPEED = 11;

export function createFlight(plan) {
  const state = {
    pos: new THREE.Vector3(),
    vel: new THREE.Vector3(),
    heading: 0,
    turnRate: 0,
    throttle: 0,
    tiltForward: 0,
    tiltSide: 0,
    crashCooldown: 0,
    nearest: Infinity,
  };
  const lastNear = new Map();
  let time = 0;

  function place(x, y, z, heading) {
    state.pos.set(x, y, z);
    state.vel.set(0, 0, 0);
    state.heading = heading;
    state.turnRate = 0;
    lastNear.clear();
  }

  function step(dt, intents, events) {
    time += dt;
    state.crashCooldown = Math.max(0, state.crashCooldown - dt);
    const targetTurn = -intents.turn * TURN;
    state.turnRate += (targetTurn - state.turnRate) * Math.min(1, dt * 6);
    state.heading += state.turnRate * dt + intents.yaw;
    intents.yaw = 0;
    const fx = Math.sin(state.heading), fz = Math.cos(state.heading);
    state.vel.x += fx * intents.forward * THRUST * dt;
    state.vel.z += fz * intents.forward * THRUST * dt;
    state.vel.y += intents.lift * LIFT * dt;
    const damp = Math.exp(-DRAG * dt), vdamp = Math.exp(-VDRAG * dt);
    state.vel.x *= damp;
    state.vel.z *= damp;
    state.vel.y *= vdamp;
    state.pos.addScaledVector(state.vel, dt);

    // The city's edges and the sky's ceiling push back softly.
    const lim = 34;
    if (state.pos.x > plan.halfX + lim) state.vel.x -= (state.pos.x - plan.halfX - lim) * 4 * dt;
    if (state.pos.x < -plan.halfX - lim) state.vel.x -= (state.pos.x + plan.halfX + lim) * 4 * dt;
    if (state.pos.z > plan.halfZ + lim) state.vel.z -= (state.pos.z - plan.halfZ - lim) * 4 * dt;
    if (state.pos.z < -plan.halfZ - lim) state.vel.z -= (state.pos.z + plan.halfZ + lim) * 4 * dt;
    if (state.pos.y > 175) state.vel.y = Math.min(state.vel.y, 0);
    if (state.pos.y < 1.2) {
      state.pos.y = 1.2;
      if (state.vel.y < 0) state.vel.y *= -0.2;
    }

    collide(events);

    const speed = Math.hypot(state.vel.x, state.vel.z);
    const forwardSpeed = state.vel.x * fx + state.vel.z * fz;
    state.throttle = Math.min(1, Math.abs(intents.forward) * 0.6 + Math.abs(intents.lift) * 0.5 + speed / 30);
    const tf = forwardSpeed * 0.016 + intents.forward * 0.1;
    const ts = state.turnRate * 0.16 * Math.min(1, speed / 10 + 0.3);
    state.tiltForward += (tf - state.tiltForward) * Math.min(1, dt * 5);
    state.tiltSide += (ts - state.tiltSide) * Math.min(1, dt * 5);
  }

  const closest = new THREE.Vector3();
  const n = new THREE.Vector3();
  function collide(events) {
    const p = state.pos;
    let nearest = Infinity;
    let nearBox = -1;
    plan.grid.query(p.x, p.z, RADIUS + NEAR + 1, (i) => {
      const b = plan.boxes[i];
      closest.set(
        Math.max(b.x - b.w / 2, Math.min(p.x, b.x + b.w / 2)),
        Math.max(b.y0, Math.min(p.y, b.y1)),
        Math.max(b.z - b.d / 2, Math.min(p.z, b.z + b.d / 2)),
      );
      n.copy(p).sub(closest);
      let d = n.length();
      if (d < RADIUS) {
        if (d < 1e-4) {
          // Inside the box: leave by the nearest face.
          const ex = b.w / 2 - Math.abs(p.x - b.x), ez = b.d / 2 - Math.abs(p.z - b.z), ey = b.y1 - p.y;
          if (ey < ex && ey < ez) n.set(0, 1, 0), (d = -ey);
          else if (ex < ez) n.set(Math.sign(p.x - b.x) || 1, 0, 0), (d = -ex);
          else n.set(0, 0, Math.sign(p.z - b.z) || 1), (d = -ez);
        } else n.divideScalar(d);
        p.addScaledVector(n, RADIUS - d);
        const impact = -state.vel.dot(n);
        if (impact > 0) {
          state.vel.addScaledVector(n, impact * 1.3);
          if (impact > 6.5 && state.crashCooldown === 0) {
            state.vel.multiplyScalar(0.45);
            state.crashCooldown = 1.2;
            events.push({ type: "crash", at: closest.clone(), impact });
          } else if (impact > 2) {
            events.push({ type: "scrape", at: closest.clone(), impact });
          }
        }
        return;
      }
      const surface = d - RADIUS;
      if (surface < nearest) {
        nearest = surface;
        nearBox = i;
      }
    });
    state.nearest = nearest;
    const speed = Math.hypot(state.vel.x, state.vel.z);
    if (nearBox >= 0 && nearest < NEAR && speed > NEAR_SPEED && state.crashCooldown === 0) {
      // Each wall pays once per pass.
      const building = plan.boxes[nearBox];
      const key = `${Math.round(building.x)}:${Math.round(building.z)}`;
      const last = lastNear.get(key) ?? -10;
      if (time - last > 2.5) {
        lastNear.set(key, time);
        events.push({ type: "near", closeness: 1 - nearest / NEAR, speed });
      }
    }
  }

  return { state, place, step };
}

// Flies the drone to a target on its own: climbs to clear the roofs between, crosses, descends over open street
// to the approach point, then moves in to the mark.
export function createAutopilot(plan) {
  let cruise = 40;
  let refresh = 0;
  let current = null;
  let final = false;
  return {
    cruise: () => cruise,
    intents(dt, s, task, out) {
      if (task !== current) {
        current = task;
        final = !task.approach;
        refresh = 0;
      }
      const goal = final ? task.point : task.approach;
      const dx = goal.x - s.pos.x, dz = goal.z - s.pos.z;
      const dist = Math.hypot(dx, dz);
      if (!final && dist < 3 && Math.abs(goal.y - s.pos.y) < 3) final = true;
      refresh -= dt;
      if (refresh <= 0) {
        refresh = 0.4;
        cruise = clearance(plan, s.pos, goal) + 7;
      }
      const desired = Math.atan2(dx, dz);
      let diff = desired - s.heading;
      diff = Math.atan2(Math.sin(diff), Math.cos(diff));
      out.turn = dist < 1.5 ? 0 : Math.max(-1, Math.min(1, -diff * 2.2));
      const wantY = dist > 16 && !final ? Math.max(cruise, goal.y) : goal.y;
      out.lift = Math.max(-1, Math.min(1, (wantY - s.pos.y) * 0.3 - s.vel.y * 0.12));
      const climbing = dist > 16 && s.pos.y < cruise - 3 && !final;
      const descending = s.pos.y > goal.y + 4 && dist < 16;
      const speed = Math.hypot(s.vel.x, s.vel.z);
      const brake = speed > dist * 0.75 + 1.5;
      out.forward = brake ? -0.6 : Math.max(0, Math.cos(diff)) * Math.min(1, dist / 22 + 0.1) * (climbing || descending ? 0.25 : 1);
      return out;
    },
  };
}

// The highest roof near the straight line between two points.
export function clearance(plan, from, to) {
  let top = 0;
  const len = Math.hypot(to.x - from.x, to.z - from.z);
  const steps = Math.max(1, Math.ceil(len / 6));
  for (let k = 0; k <= steps; k++) {
    const t = k / steps;
    const x = from.x + (to.x - from.x) * t, z = from.z + (to.z - from.z) * t;
    plan.grid.query(x, z, 4, (i) => {
      const b = plan.boxes[i];
      if (Math.abs(x - b.x) < b.w / 2 + 3 && Math.abs(z - b.z) < b.d / 2 + 3) top = Math.max(top, b.y1);
    });
  }
  return top;
}
