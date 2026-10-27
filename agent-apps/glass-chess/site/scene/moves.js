// How pieces move: a lift along an arc with its shadow sliding and spreading beneath it, a landing that settles with
// a small squash and a ring of dust, a captured piece that sinks into the board while the mirror ripples, a promotion
// that turns the pawn into its new piece on landing, and a beaten king that tips over. With reduced motion, a move is
// a short cross-fade from one square to the other and nothing tips.
import * as THREE from "three";
import { squareXZ } from "./board.js";

export const ease = {
  inOut: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  out: (t) => 1 - Math.pow(1 - t, 3),
  in: (t) => t * t * t,
  // A settle that overshoots once, for the landing squash.
  spring: (t) => 1 - Math.exp(-7 * t) * Math.cos(11 * t),
};

export class Tweens {
  constructor() { this.list = []; }

  add(duration, update, delay = 0) {
    return new Promise((resolve) => {
      this.list.push({ start: performance.now() / 1000 + delay, duration, update, resolve });
    });
  }

  get busy() { return this.list.length > 0; }

  tick(now) {
    if (!this.list.length) return;
    const keep = [];
    for (const tw of this.list) {
      if (now < tw.start) { keep.push(tw); continue; }
      const t = Math.min(1, (now - tw.start) / tw.duration);
      tw.update(t);
      if (t < 1) keep.push(tw); else tw.resolve();
    }
    this.list = keep;
  }

  finishAll() {
    for (const tw of this.list) { tw.update(1); tw.resolve(); }
    this.list = [];
  }
}

const AXIS = new THREE.Vector3();
const UP = new THREE.Vector3(0, 1, 0);

// Flies one piece from one square to another; resolves when it has landed.
export function fly(world, piece, from, to, { reduced, hop = 1, onLand } = {}) {
  const [x0, z0] = squareXZ(from);
  const [x1, z1] = squareXZ(to);
  const dist = Math.hypot(x1 - x0, z1 - z0);
  const g = piece.group;
  if (reduced) {
    return world.tweens.add(0.22, (t) => {
      const fadeOut = t < 0.5;
      piece.fade(fadeOut ? 1 - t * 2 : (t - 0.5) * 2);
      if (!fadeOut) g.position.set(x1, 0, z1);
      if (t === 1) { piece.fade(1); onLand?.(); }
    });
  }
  const duration = Math.min(0.72, 0.4 + dist * 0.045) * (hop > 1 ? 1.1 : 1);
  const height = (0.38 + dist * 0.07) * hop;
  AXIS.set(z1 - z0, 0, -(x1 - x0)).normalize();
  const flight = world.tweens.add(duration, (t) => {
    const k = ease.inOut(t);
    g.position.set(x0 + (x1 - x0) * k, height * Math.sin(Math.PI * t), z0 + (z1 - z0) * k);
    // The piece leans into its travel and rights itself as it lands.
    g.quaternion.setFromAxisAngle(AXIS, -0.16 * Math.sin(Math.PI * t) * Math.min(1, dist / 2));
    piece.lift = g.position.y;
  });
  return flight.then(() => {
    g.position.set(x1, 0, z1);
    g.quaternion.identity();
    piece.lift = 0;
    world.dust.burst(x1, z1, world.now, 1.5 + piece.height * 0.4, 0.9);
    onLand?.();
    // The settle runs on its own; the move counts as done the moment the piece touches down.
    world.tweens.add(0.32, (t) => {
      const s = 1 - 0.06 * (1 - ease.spring(t));
      piece.mesh.scale.set(2 - s, s, 2 - s);
    });
  });
}

// The taken piece sinks below the lacquer with a ripple running out from it.
export function sink(world, piece, square, { reduced } = {}) {
  world.board.rippleAt(square, world.now, 1);
  const g = piece.group;
  if (reduced) {
    return world.tweens.add(0.2, (t) => { piece.fade(1 - t); }).then(() => world.removePiece(piece));
  }
  const depth = piece.height * 1.05;
  return world.tweens.add(0.62, (t) => {
    const k = ease.in(t);
    g.position.y = -depth * k;
    g.rotation.y = k * 0.6;
    piece.sinking = k;
  }).then(() => world.removePiece(piece));
}

// The beaten king tips over away from the piece that mated it and settles with a small bounce.
export function tip(world, piece, awayFrom) {
  const [kx, kz] = squareXZ(piece.square);
  const [ax, az] = squareXZ(awayFrom);
  const dir = new THREE.Vector3(kx - ax, 0, kz - az);
  if (dir.lengthSq() < 1e-6) dir.set(1, 0, 0);
  dir.normalize();
  const axis = new THREE.Vector3().crossVectors(UP, dir).normalize();
  const pivot = new THREE.Vector3(kx, 0, kz).addScaledVector(dir, piece.radius);
  const g = piece.group;
  const base = new THREE.Vector3(kx, 0, kz);
  const q = new THREE.Quaternion();
  const off = new THREE.Vector3();
  const rest = Math.PI / 2 - 0.12;
  return world.tweens.add(1.1, (t) => {
    // Falls with gravity, then a damped rebound on the board.
    let a;
    if (t < 0.62) a = rest * Math.pow(t / 0.62, 2);
    else { const u = (t - 0.62) / 0.38; a = rest - 0.16 * Math.exp(-4 * u) * Math.abs(Math.sin(u * Math.PI * 2.2)); }
    q.setFromAxisAngle(axis, a);
    off.copy(base).sub(pivot).applyQuaternion(q);
    g.position.copy(pivot).add(off);
    g.quaternion.copy(q);
    piece.tipped = a / rest;
  }, 0.35);
}
