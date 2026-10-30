// The story film's one camera. It opens on the whole wall of dim tiles and dives to day one; it holds each card at its
// station (the print large in the frame, the wall around it), pushing in through one hold and easing back out through
// the next; between two cards it makes the move the board names (a crane, a glide, a sweep, a swing or a reveal,
// each with its own pull away from the wall, tip, bank, turn and ease, winding back before it goes and landing
// past its mark); and at the end it pulls back to the whole wall. Every framing shows the wall alone: a move that
// would reach past the wall's edge slides back inside it.
import * as THREE from 'three';
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, mixPt, smooth, type Pt} from '../../system/three/motion';
import type {Travel} from '../../system/three/travel';
import type {Card, Move, Plan} from './plan';

/** What the camera frames: a wall point at the middle of the picture, `h` wall px tall at depth `z`, and how it is turned. */
export type Framing = {c: Pt; h: number; z: number; fov: number; yaw: number; pitch: number; roll: number};

export const poseOf = (plan: Plan, f: Framing): Pose => {
  const target: [number, number, number] = [f.c[0] - plan.W / 2, plan.H / 2 - f.c[1], f.z];
  const D = f.h / 2 / Math.tan((f.fov * Math.PI) / 360);
  const cp = Math.cos(f.pitch);
  return {
    position: [target[0] + D * Math.sin(f.yaw) * cp, target[1] - D * Math.sin(f.pitch), target[2] + D * Math.cos(f.yaw) * cp],
    target, roll: f.roll, fov: f.fov,
  };
};

export const stationOf = (c: Card): Framing => ({c: c.station.c, h: c.station.h, z: c.lift, fov: c.station.fov, yaw: 0, pitch: 0, roll: 0});

const wallFraming = (plan: Plan): Framing => ({c: plan.closer.frame.c, h: plan.closer.frame.h, z: 0, fov: plan.closer.frame.fov, yaw: 0, pitch: 0, roll: 0});

const mixF = (a: Framing, b: Framing, u: number): Framing => ({
  c: mixPt(a.c, b.c, u), h: a.h * Math.pow(b.h / a.h, u), z: lerp(a.z, b.z, u), fov: lerp(a.fov, b.fov, u),
  yaw: lerp(a.yaw, b.yaw, u), pitch: lerp(a.pitch, b.pitch, u), roll: lerp(a.roll, b.roll, u),
});

/** The most a move pulls away to, a share of the wall's height (or its own framing's, when that is larger). */
const PULL_MOST = 0.8;

/** A move from `a` to `b` at progress `u` (already eased, so it runs a little under 0 as it winds back and a little over
 * 1 as it lands past its mark): it pulls away from the wall by `m.arc` at its middle, tips toward the way it travels up
 * or down by `m.pitch`, and banks and turns toward the way it travels across. */
const travel = (plan: Plan, a: Framing, b: Framing, u: number, m: Move | null): Framing => {
  const f = mixF(a, b, u);
  if (!m) return f;
  const bell = Math.sin(Math.PI * clamp01(u));
  const far = Math.max(a.h, b.h);
  const lx = Math.max(-1, Math.min(1, (2 * (b.c[0] - a.c[0])) / far));
  const ly = Math.max(-1, Math.min(1, (2 * (b.c[1] - a.c[1])) / far));
  const side = lx === 0 ? 1 : Math.sign(lx);
  return {
    ...f, h: Math.min(f.h * (1 + m.arc * bell), Math.max(f.h, PULL_MOST * plan.H)),
    yaw: f.yaw - m.yaw * lx * bell, pitch: f.pitch - m.pitch * ly * bell, roll: f.roll + m.bank * side * Math.abs(lx) * bell,
  };
};

/** The framing at a share `p` (0 to 1) of a card's hold: every other card pushes in, the ones between start pushed in
 * and ease back out, so the holds alternate in direction and none leaves the range the board's check measures. */
const holding = (c: Card, index: number, p: number): Framing => {
  const st = stationOf(c);
  const e = smooth(p);
  const k = index % 2 === 0 ? e : 1 - e;
  return {...st, h: st.h * (1 - c.push * k)};
};

/** The framing a card's hold ends on. */
const endOf = (c: Card, index: number) => holding(c, index, 1);

/** The camera's framing at beat `t`, kept on the wall. */
export const framingAt = (plan: Plan, t: number): Framing => inside(plan, framed(plan, t));

const framed = (plan: Plan, t: number): Framing => {
  const cards = plan.cards;
  const first = cards[0];
  // the dive from the whole wall of dim tiles onto day one, landing a hair past it
  if (t < first.arrive) return mixF(wallFraming(plan), holding(first, 0, 0), bezier([0.5, 0, 0.2, 1.04])(clamp01(t / first.arrive)));
  for (let i = 0; i < cards.length; i++) {
    const c = cards[i];
    if (t < c.arrive) continue;
    if (t <= c.leave) return holding(c, i, clamp01((t - c.arrive) / Math.max(0.1, c.leave - c.arrive)));
    const next = cards[i + 1];
    if (next && t < next.arrive) {
      const u = bezier(next.move?.ease ?? plan.ease.move)(clamp01((t - c.leave) / (next.arrive - c.leave)));
      return travel(plan, endOf(c, i), holding(next, i + 1, 0), u, next.move);
    }
  }
  // the pull back from the latest to the whole wall, settling into its framing exactly
  const last = cards.length - 1;
  const C = plan.closer.at;
  const end = wallFraming(plan);
  if (t >= C + plan.closer.move) return end;
  const u = bezier([0.5, -0.1, 0.25, 1])(clamp01((t - C) / plan.closer.move));
  return mixF(endOf(cards[last], last), end, u);
};

/** The share of the picture's height kept between what the camera sees and the wall's edge. */
const MARGIN = 0.02;

/** `f` slid to show the wall alone: what the camera sees of the wall (the picture's four corners cast onto it) kept
 * MARGIN inside its edges, and centered on it where it is as large as the wall. */
const inside = (plan: Plan, f: Framing): Framing => {
  const pose = poseOf(plan, f);
  setCam(probe, pose, plan.W / plan.H);
  const pos = probe.position;
  const xs: number[] = [];
  const ys: number[] = [];
  for (const [nx, ny] of [[-1, -1], [1, -1], [1, 1], [-1, 1]]) {
    const d = new THREE.Vector3(nx, ny, 0.5).unproject(probe).sub(pos);
    const k = d.z < -1e-6 ? -pos.z / d.z : 1e6;
    xs.push(pos.x + d.x * k + plan.W / 2);
    ys.push(plan.H / 2 - (pos.y + d.y * k));
  }
  const keep = (lo: number, hi: number, size: number) => {
    const m = MARGIN * (Math.max(...ys) - Math.min(...ys));
    if (hi - lo + 2 * m >= size) return size / 2 - (lo + hi) / 2;
    return Math.max(0, m - lo) - Math.max(0, hi - (size - m));
  };
  const dx = keep(Math.min(...xs), Math.max(...xs), plan.W);
  const dy = keep(Math.min(...ys), Math.max(...ys), plan.H);
  return dx === 0 && dy === 0 ? f : {...f, c: [f.c[0] + dx, f.c[1] + dy]};
};

const cam = new THREE.PerspectiveCamera();
const probe = new THREE.PerspectiveCamera();
const setCam = (cam: THREE.PerspectiveCamera, p: Pose, aspect: number) => {
  cam.position.set(...p.position);
  const fwd = new THREE.Vector3(p.target[0] - p.position[0], p.target[1] - p.position[1], p.target[2] - p.position[2]).normalize();
  cam.up.copy(new THREE.Vector3(0, 1, 0).applyAxisAngle(fwd, -p.roll));
  cam.lookAt(...p.target);
  cam.fov = p.fov;
  cam.aspect = aspect;
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld();
};

/** How much of the picture's motion over the last half frame the shutter keeps: a light blur that reads as the
 * camera moving and never wipes the picture out. */
const SHUTTER = 0.35;

/** The pose at beat `t` and the finishing pass for it: only the shutter's light blur of the camera's own motion, no
 * zoom blur, no warp and no burn. */
export const shotAt = (plan: Plan, t: number): {pose: Pose; travel: Travel} => {
  const pose = poseOf(plan, framingAt(plan, t));
  const prev = poseOf(plan, framingAt(plan, t - 0.5 / plan.pulse));
  const aspect = plan.W / plan.H;
  const p = new THREE.Vector3(...pose.target);
  setCam(cam, prev, aspect);
  const a = p.clone().project(cam);
  setCam(cam, pose, aspect);
  const b = p.clone().project(cam);
  const smear: [number, number] = [(b.x - a.x) * 0.5 * SHUTTER, (b.y - a.y) * 0.5 * SHUTTER];
  return {
    pose,
    // the operator's hand moves with the film's time, which stops where the closer's picture stops
    travel: {zoom: 0, center: [0.5, 0.5], smear: Math.hypot(...smear) < 0.0008 ? [0, 0] : smear, warp: 0, burn: 0, vignette: 0,
      time: Math.min(t, plan.closer.still) * 0.25},
  };
};
