// Walking on a sphere. The explorer's position is a point on the planet; its heading, the camera's forward, its
// velocity, and the sun's bearing are tangent vectors carried along (parallel transport) as it moves, so "forward"
// always means forward on the ground under its feet. Gravity points at the planet's center.
import * as THREE from "three";
import { RADIUS, WADE_DEPTH } from "./generation.js";

export const WALK_SPEED = 4.2;
export const RUN_SPEED = 7.5;
const WATER_FACTOR = 0.55;
const JUMP_SPEED = 7.2;
const GRAVITY = 22;
const ALIGN_DELAY = 1.2;

function tangent(v, up) {
  return v.addScaledVector(up, -v.dot(up)).normalize();
}

export function createWalker(terrain) {
  const pos = new THREE.Vector3();
  const up = new THREE.Vector3();
  const heading = new THREE.Vector3();
  const forward = new THREE.Vector3();
  const sunAz = new THREE.Vector3();
  const vel = new THREE.Vector3();
  const normal = new THREE.Vector3();
  const move = new THREE.Vector3();
  const right = new THREE.Vector3();
  const next = new THREE.Vector3();
  const ahead = new THREE.Vector3();
  const q = new THREE.Quaternion();

  const state = {
    pos, up, heading, forward, sunAz, vel,
    radius: RADIUS, vy: 0, grounded: true, pitch: 0.62, speed: 0, turn: 0,
    slopePitch: 0, slopeRoll: 0, surface: "grass", inWater: false, sinceDrag: 99, stride: 0,
  };

  const ground = (d) => Math.max(terrain.height(d.x, d.y, d.z), WADE_DEPTH);

  function surfaceAt(d) {
    const h = terrain.height(d.x, d.y, d.z);
    if (h < -0.05) return "water";
    if (h < 0.28) return "sand";
    if (h > terrain.snowline) return "snow";
    terrain.groundNormal(d, normal);
    return normal.dot(d) < 0.8 ? "rock" : "grass";
  }

  // Face the explorer toward `facing` (a direction on the planet), with the sun ahead and to the right.
  function reset(startDir, facing, sunTurn = 1.05) {
    up.set(...startDir).normalize();
    forward.copy(facing);
    tangent(forward, up);
    if (!(forward.lengthSq() > 0.5)) forward.set(Math.abs(up.y) < 0.9 ? 0 : 1, Math.abs(up.y) < 0.9 ? 1 : 0, 0);
    tangent(forward, up);
    heading.copy(forward);
    sunAz.copy(forward).applyAxisAngle(up, -sunTurn);
    vel.set(0, 0, 0);
    state.radius = RADIUS + ground(up);
    pos.copy(up).multiplyScalar(state.radius);
    state.vy = 0;
    state.grounded = true;
    state.speed = 0;
    state.stride = 0;
    state.sinceDrag = 99;
  }

  // input: { x, y, run, jump, yaw, pitch, dragging }. Returns the events of this step.
  function step(dt, input) {
    const events = [];
    if (input.yaw) forward.applyAxisAngle(up, -input.yaw);
    state.pitch = THREE.MathUtils.clamp(state.pitch + (input.pitch || 0), 0, 1);
    state.sinceDrag = input.dragging || input.yaw ? 0 : state.sinceDrag + dt;

    right.crossVectors(forward, up).normalize();
    move.copy(forward).multiplyScalar(input.y).addScaledVector(right, input.x);
    const amount = Math.min(1, move.length());
    if (amount > 0.001) move.normalize();

    const h0 = ground(up);
    state.inWater = terrain.height(up.x, up.y, up.z) < -0.05;
    let speed = (input.run ? RUN_SPEED : WALK_SPEED) * amount * (state.inWater ? WATER_FACTOR : 1);
    if (amount > 0.001) {
      ahead.copy(up).addScaledVector(move, 0.03).normalize();
      const rise = (ground(ahead) - h0) / (0.03 * RADIUS);
      if (rise > 0) speed /= 1 + rise * 1.1;
    }

    const accel = state.grounded ? 14 : 3.5;
    const k = 1 - Math.exp(-accel * dt);
    vel.lerp(move.multiplyScalar(speed), k);
    vel.addScaledVector(up, -vel.dot(up));
    move.normalize();

    const before = heading.clone();
    if (amount > 0.1) {
      heading.lerp(move, 1 - Math.exp(-dt * 11));
      tangent(heading, up);
    }
    state.turn = THREE.MathUtils.damp(state.turn, before.cross(heading).dot(up) / Math.max(dt, 1e-4), 10, dt);

    if (state.sinceDrag > ALIGN_DELAY && amount > 0.1 && heading.dot(forward) > -0.3) {
      forward.lerp(heading, 1 - Math.exp(-dt * 2.2));
      tangent(forward, up);
    }

    // Move along the ground, then carry every tangent vector to the new point.
    next.copy(up).multiplyScalar(state.radius).addScaledVector(vel, dt).normalize();
    q.setFromUnitVectors(up, next);
    for (const t of [heading, forward, sunAz, vel]) t.applyQuaternion(q);
    up.copy(next);
    for (const t of [heading, forward, sunAz]) tangent(t, up);
    vel.addScaledVector(up, -vel.dot(up));

    const groundRadius = RADIUS + ground(up);
    if (state.grounded && input.jump) {
      state.vy = JUMP_SPEED;
      state.grounded = false;
      events.push({ type: "jump" });
    }
    if (state.grounded) {
      if (state.radius - groundRadius > 0.35) {
        state.grounded = false;
        state.vy = 0;
      } else {
        state.radius = groundRadius;
      }
    }
    if (!state.grounded) {
      state.vy -= GRAVITY * dt;
      state.radius += state.vy * dt;
      if (state.radius <= groundRadius) {
        events.push({ type: "land", impact: -state.vy, surface: surfaceAt(up) });
        state.radius = groundRadius;
        state.vy = 0;
        state.grounded = true;
      }
    }
    pos.copy(up).multiplyScalar(state.radius);

    state.speed = vel.length();
    if (state.grounded && state.speed > 0.5) {
      state.stride += state.speed * dt;
      const stepLength = input.run ? 1.35 : 1.05;
      if (state.stride > stepLength) {
        state.stride -= stepLength;
        state.surface = surfaceAt(up);
        events.push({ type: "step", surface: state.surface, run: !!input.run });
      }
    }

    terrain.groundNormal(up, normal);
    right.crossVectors(up, heading).normalize();
    state.slopePitch = THREE.MathUtils.damp(state.slopePitch, -normal.dot(heading), 8, dt);
    state.slopeRoll = THREE.MathUtils.damp(state.slopeRoll, normal.dot(right), 8, dt);
    return events;
  }

  return { state, reset, step };
}
