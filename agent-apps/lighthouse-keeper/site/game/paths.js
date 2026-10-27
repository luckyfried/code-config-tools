// Ship paths: each ship steers toward the reef along a curve, its heading eased under a capped turn rate, and the
// state the beam acts on: the hold that fills the ring, the warmth, the burn, and the wreck.
import { REEF_RADIUS } from "../scene/lighthouse.js";

export const HOLD_SECONDS = 1.45;

export function emptyShip() {
  return {
    active: false,
    x: 0,
    z: 0,
    heading: 0,
    speed: 0,
    curve: 0,
    phase: 0,
    age: 0,
    fill: 0,
    burn: 0,
    heat: 0,
    fade: 1,
    turned: false,
    turnedAt: 0,
    wrecked: false,
    sink: 0,
    holdRate: 1,
  };
}

export function bearingOf(x, z) {
  return Math.atan2(x, -z);
}

export function angleDiff(a, b) {
  let d = a - b;
  while (d > Math.PI) d -= Math.PI * 2;
  while (d < -Math.PI) d += Math.PI * 2;
  return d;
}

export function launch(ship, bearing, distance, speed, curve, phase) {
  ship.active = true;
  ship.x = Math.sin(bearing) * distance;
  ship.z = -Math.cos(bearing) * distance;
  ship.heading = bearing + Math.PI + curve * 0.6;
  ship.speed = speed;
  ship.curve = curve;
  ship.phase = phase;
  ship.age = 0;
  ship.fill = 0;
  ship.burn = 0;
  ship.heat = 0;
  ship.fade = 1;
  ship.turned = false;
  ship.wrecked = false;
  ship.sink = 0;
  ship.holdRate = 1;
}

// Moves one ship one step. Returns "wreck" the step it reaches the reef, "gone" the step it finishes burning or
// sinking, and null otherwise.
export function steer(ship, dt) {
  if (!ship.active) return null;
  ship.age += dt;
  if (ship.turned) {
    ship.burn = Math.min(1, ship.burn + dt / 1.35);
    ship.speed *= Math.pow(0.25, dt);
    ship.heat = Math.max(0, ship.heat - dt);
    advance(ship, dt);
    if (ship.burn >= 1) {
      ship.active = false;
      return "gone";
    }
    return null;
  }
  if (ship.wrecked) {
    ship.sink = Math.min(1, ship.sink + dt / 3.2);
    ship.speed *= Math.pow(0.1, dt);
    advance(ship, dt);
    if (ship.sink >= 1) {
      ship.active = false;
      return "gone";
    }
    return null;
  }
  const toReef = bearingOf(-ship.x, -ship.z);
  const dist = Math.hypot(ship.x, ship.z);
  const swing = ship.curve * Math.min(1, (dist - REEF_RADIUS) / 60) * Math.sin(ship.age * 0.32 + ship.phase);
  const want = toReef + swing;
  const turn = angleDiff(want, ship.heading);
  const maxTurn = 0.35 * dt;
  ship.heading += Math.max(-maxTurn, Math.min(maxTurn, turn * 1.5 * dt));
  advance(ship, dt);
  if (dist < REEF_RADIUS + 1.5) {
    ship.wrecked = true;
    return "wreck";
  }
  return null;
}

function advance(ship, dt) {
  ship.x += Math.sin(ship.heading) * ship.speed * dt;
  ship.z += -Math.cos(ship.heading) * ship.speed * dt;
}

// The beam acts on a ship: the hold fills while it is in the cone and drains slowly when it leaves; the sails burn
// as the hold rises; a full hold turns the ship back.
export function hold(ship, inBeam, dt) {
  if (!ship.active || ship.turned || ship.wrecked) return false;
  ship.heat += ((inBeam ? 1 : 0) - ship.heat) * Math.min(1, dt * 5);
  if (inBeam) ship.fill = Math.min(1, ship.fill + (dt / HOLD_SECONDS) * ship.holdRate);
  else ship.fill = Math.max(0, ship.fill - dt * 0.22);
  ship.burn = Math.max(ship.burn, ship.fill * 0.42);
  if (ship.fill >= 1) {
    ship.turned = true;
    return true;
  }
  return false;
}
