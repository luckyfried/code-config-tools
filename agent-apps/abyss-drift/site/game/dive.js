// One dive: the sub's motion inside the trench, the air, and the ascent. The air includes the climb back, so the
// reserve (the time it takes to surface from here) is always shown, and reaching it starts the ascent.
import * as THREE from "three";
import { FLOOR_DEPTH } from "./species.js";

export const MOTION = {
  forward: 6.5,
  reverse: 2.5,
  accel: 4.5,
  turn: 1.15,
  descend: 11,
  rise: 4.5,
  ascent: 16,
  margin: 4,
};

const c2 = new THREE.Vector2();

export function createDive(world, airSeconds) {
  const shape = world.shape;
  const vents = world.trench.vents;
  const sub = {
    pos: new THREE.Vector3(),
    vel: new THREE.Vector3(),
    yaw: 0,
    yawRate: 0,
    pitch: 0,
    roll: 0,
    speed: 0,
  };
  const st = {
    sub,
    air: airSeconds,
    airTotal: airSeconds,
    ascending: false,
    forced: false,
    surfaced: false,
    maxDepth: 0,
    time: 0,
  };

  function depth() {
    return Math.max(0, -sub.pos.y);
  }

  /** Seconds of air the climb from here takes, plus the margin. */
  function reserve() {
    return depth() / MOTION.ascent + MOTION.margin;
  }

  /** The deepest point the sub can reach with the air left and still climb back. */
  function reach() {
    const d = depth();
    const spare = st.air - MOTION.margin + d / MOTION.descend;
    return Math.max(d, Math.min(FLOOR_DEPTH, spare / (1 / MOTION.ascent + 1 / MOTION.descend)));
  }

  return {
    st,
    sub,
    depth,
    reserve,
    reach,
    start(yaw = 0) {
      shape.center(3, c2);
      sub.pos.set(c2.x, -3, c2.y);
      sub.vel.set(0, 0, 0);
      sub.yaw = yaw;
      sub.yawRate = 0;
      sub.pitch = 0;
      sub.roll = 0;
      st.air = st.airTotal;
      st.ascending = false;
      st.forced = false;
      st.surfaced = false;
      st.maxDepth = 0;
      st.time = 0;
    },
    beginAscent(forced) {
      if (st.ascending) return false;
      st.ascending = true;
      st.forced = forced;
      return true;
    },
    /** One fixed step. intent: { thrust, turn, descend, rise }. Answers events: "reserve", "surfaced". */
    step(dt, intent) {
      const events = [];
      st.time += dt;
      st.air = Math.max(0, st.air - dt);
      if (!st.ascending && st.air <= reserve()) {
        st.ascending = true;
        st.forced = true;
        events.push("reserve");
      }
      // Heading.
      const turnWant = intent.turn * MOTION.turn;
      sub.yawRate += (turnWant - sub.yawRate) * (1 - Math.exp(-dt * 3));
      sub.yaw += sub.yawRate * dt;
      // Forward speed along the heading.
      const fw = intent.thrust >= 0 ? intent.thrust * MOTION.forward : intent.thrust * MOTION.reverse;
      const want = st.ascending ? Math.max(fw * 0.6, 0) : fw;
      sub.speed += (want - sub.speed) * (1 - Math.exp(-dt * (MOTION.accel / Math.max(1, Math.abs(want - sub.speed)) + 0.6)));
      const hx = Math.sin(sub.yaw), hz = Math.cos(sub.yaw);
      sub.vel.x += (hx * sub.speed - sub.vel.x) * (1 - Math.exp(-dt * 2.5));
      sub.vel.z += (hz * sub.speed - sub.vel.z) * (1 - Math.exp(-dt * 2.5));
      // Vertical: descend, rise, hold, or the ascent.
      let vy = 0;
      if (st.ascending) vy = MOTION.ascent;
      else if (intent.descend) vy = -MOTION.descend;
      else if (intent.rise) vy = MOTION.rise;
      const k = st.ascending ? 1.2 : intent.descend ? 1.6 : 2.4;
      sub.vel.y += (vy - sub.vel.y) * (1 - Math.exp(-dt * k));
      sub.pos.addScaledVector(sub.vel, dt);

      // Keep inside the trench, the floor, and the chimneys.
      const d = Math.max(0, -sub.pos.y);
      shape.center(d, c2);
      const rx = sub.pos.x - c2.x, rz = sub.pos.z - c2.y;
      const rr = Math.hypot(rx, rz);
      const lim = shape.radius(d) - 12;
      if (rr > lim) {
        sub.pos.x = c2.x + (rx / rr) * lim;
        sub.pos.z = c2.y + (rz / rr) * lim;
        sub.vel.x *= 0.5;
        sub.vel.z *= 0.5;
        if (rr > lim + 0.5) events.push("bump");
      }
      const floor = world.trench.floorHeight(sub.pos.x, sub.pos.z) + 2.6;
      if (sub.pos.y < floor) {
        sub.pos.y = floor;
        sub.vel.y = Math.max(0, sub.vel.y);
      }
      for (const v of vents) {
        const dx = sub.pos.x - v.x, dz = sub.pos.z - v.z;
        const dd = Math.hypot(dx, dz), minD = v.radius + 3.2;
        if (dd < minD && sub.pos.y < v.top + 2) {
          sub.pos.x = v.x + (dx / (dd || 1)) * minD;
          sub.pos.z = v.z + (dz / (dd || 1)) * minD;
        }
      }
      if (sub.pos.y > -1.5) {
        sub.pos.y = -1.5;
        sub.vel.y = Math.min(0, sub.vel.y);
        if (st.ascending && !st.surfaced) {
          st.surfaced = true;
          events.push("surfaced");
        }
      }
      // Attitude: nose down when diving, nose up on the ascent, bank into turns.
      const pitchWant = THREE.MathUtils.clamp(-sub.vel.y * 0.035, -0.4, 0.4);
      sub.pitch += (pitchWant - sub.pitch) * (1 - Math.exp(-dt * 2));
      sub.roll += (-sub.yawRate * 0.28 - sub.roll) * (1 - Math.exp(-dt * 3));
      st.maxDepth = Math.max(st.maxDepth, Math.max(0, -sub.pos.y));
      return events;
    },
  };
}
