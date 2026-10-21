// The drive film's one camera: a station at every card (the card's piece frame filling the picture, pushing in), an
// eased move between stations that pulls back, banks and looks ahead along the travel, a graze along the ribbon, and
// the closer's framing it settles into exactly.
import * as THREE from 'three';
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, mixPt, span, type Pt} from '../../system/three/motion';
import type {Travel} from '../../system/three/travel';
import {placeOnWall, type Card, type Plan} from './plan';
import {cardScale, liftOf} from './card';

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

const HOLD_FOV = 30;
const CLOSER_FOV = 18;

/** The framing that shows card `c`'s piece frame whole. */
export const stationOf = (plan: Plan, c: Card): Framing => {
  const s = cardScale(c);
  return {c: [c.T.o[0] + s * plan.W / 2, c.T.o[1] + s * plan.H / 2], h: plan.H * s, z: liftOf(c), fov: HOLD_FOV, yaw: 0, pitch: 0, roll: 0};
};

const closerFraming = (plan: Plan): Framing => ({c: [plan.W / 2, plan.H / 2], h: plan.H, z: 0, fov: CLOSER_FOV, yaw: 0, pitch: 0, roll: 0});

const mixF = (a: Framing, b: Framing, u: number): Framing => ({
  c: mixPt(a.c, b.c, u), h: a.h * Math.pow(b.h / a.h, u), z: lerp(a.z, b.z, u), fov: lerp(a.fov, b.fov, u),
  yaw: lerp(a.yaw, b.yaw, u), pitch: lerp(a.pitch, b.pitch, u), roll: lerp(a.roll, b.roll, u),
});

/** A move from `a` to `b` at progress `u` (already eased): it pulls back by `arc` at its middle, banks and looks ahead along the travel. */
const travel = (a: Framing, b: Framing, u: number, arc: number): Framing => {
  const m = mixF(a, b, u);
  const bell = Math.sin(Math.PI * u);
  const dx = b.c[0] - a.c[0];
  const dy = b.c[1] - a.c[1];
  const scale = Math.max(a.h, b.h);
  const lx = Math.max(-1, Math.min(1, dx / scale));
  const ly = Math.max(-1, Math.min(1, dy / scale));
  return {...m, h: m.h * (1 + arc * bell), yaw: m.yaw - 0.42 * lx * bell, pitch: m.pitch - 0.3 * ly * bell, roll: m.roll + 0.1 * lx * bell, fov: m.fov + 10 * bell};
};

export type Shot = {framing: Framing; travel: Partial<Travel>};

/** The camera's framing at beat `t`, with the extra travel treatment the move between two stations carries. */
export const framingAt = (plan: Plan, t: number): Shot => {
  const move = bezier(plan.ease.move);
  const cards = plan.cards;
  const R = plan.ribbon.at;
  const C = plan.closer.at;
  const last = cards[cards.length - 1];
  // the stations, in film order
  for (let i = 0; i < cards.length; i++) {
    const c = cards[i];
    const st = stationOf(plan, c);
    const from = i === 0 ? 0 : c.arrive + 0.25;
    const to = c.leave - 0.6;
    if (t < from) continue;
    if (t <= to || (i === cards.length - 1 && t <= to)) {
      const hold = clamp01((t - from) / Math.max(0.1, to - from));
      const push = 1 - 0.045 * hold;
      const open = i === 0 ? 1 + 0.12 * (1 - span(t, 0, 0.35, bezier([0.2, 0.9, 0.3, 1]))) : 1;
      return {framing: {...st, h: st.h * push * open}, travel: {}};
    }
    const next = cards[i + 1];
    if (next && t < next.arrive + 0.25) {
      const u = move(clamp01((t - to) / (next.arrive + 0.25 - to)));
      const a = {...st, h: st.h * 0.955};
      const b = stationOf(plan, next);
      const far = Math.hypot(b.c[0] - a.c[0], b.c[1] - a.c[1]) / Math.max(a.h, b.h);
      const tr: Partial<Travel> = {};
      if (c.hook) tr.warp = 0.035 * Math.sin(Math.PI * u);
      if (next === last) tr.burn = Math.sin(Math.PI * clamp01((t - to + 0.2) / (next.arrive + 0.45 - to)));
      return {framing: travel(a, b, u, 0.25 + 0.5 * Math.min(1, far)), travel: tr};
    }
  }
  // the ribbon: down into a graze along the bars, then up into the closer's framing
  const st = {...stationOf(plan, last), h: stationOf(plan, last).h * 0.955};
  // the graze keeps the top post's count in the picture: its left end stays inside the near (left) half of the frame
  const left = last.count ? placeOnWall(last.T, last.count).at[0] : 0;
  const gx = (h: number, want: number) => Math.min(want, left + 0.55 * h * (plan.W / plan.H) / 2);
  const g0: Framing = {c: [gx(plan.H * 0.64, plan.W * 0.42), plan.H * 0.74], h: plan.H * 0.64, z: 60, fov: 46, yaw: -0.38, pitch: 0.6, roll: 0.12};
  const g1: Framing = {c: [gx(plan.H * 0.6, plan.W * 0.42), plan.H * 0.4], h: plan.H * 0.6, z: 60, fov: 46, yaw: 0.32, pitch: 0.55, roll: -0.1};
  const end = closerFraming(plan);
  const a0 = last.leave - 0.6;
  const a1 = R + 0.6;
  const a2 = R + 2.0;
  if (t < a1) return {framing: mixF(st, g0, move(clamp01((t - a0) / (a1 - a0)))), travel: {}};
  if (t < a2) return {framing: mixF(g0, g1, span(t, a1, a2 - a1, (u) => u)), travel: {}};
  if (t < C) return {framing: mixF(g1, end, move(clamp01((t - a2) / (C - a2)))), travel: {}};
  const settle = span(t, C, Math.max(0.5, plan.closer.still - C), bezier([0.2, 0.6, 0.3, 1]));
  return {framing: {...end, h: end.h * (1 + 0.03 * (1 - settle))}, travel: {}};
};

const cam = new THREE.PerspectiveCamera();
const setCam = (p: Pose, aspect: number) => {
  cam.position.set(...p.position);
  const fwd = new THREE.Vector3(p.target[0] - p.position[0], p.target[1] - p.position[1], p.target[2] - p.position[2]).normalize();
  cam.up.copy(new THREE.Vector3(0, 1, 0).applyAxisAngle(fwd, -p.roll));
  cam.lookAt(...p.target);
  cam.fov = p.fov;
  cam.aspect = aspect;
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld();
};

/** The pose at beat `t` and the travel pass for it: the blur of the move the shutter saw over the last half frame, the vignette, the chosen treatment. */
export const shotAt = (plan: Plan, t: number): {pose: Pose; travel: Travel} => {
  const now = framingAt(plan, t);
  const half = 0.5 / plan.pulse;
  const was = framingAt(plan, t - half);
  const pose = poseOf(plan, now.framing);
  const prev = poseOf(plan, was.framing);
  const aspect = plan.W / plan.H;
  const p = new THREE.Vector3(...pose.target);
  setCam(prev, aspect);
  const a = p.clone().project(cam);
  setCam(pose, aspect);
  const b = p.clone().project(cam);
  const cap = (v: number, m: number) => Math.max(-m, Math.min(m, v));
  const smear: [number, number] = [cap((b.x - a.x) * 0.5, 0.09), cap((b.y - a.y) * 0.5, 0.09)];
  const zoom = Math.min(0.18, Math.abs(Math.log(was.framing.h / now.framing.h)) * 2.2);
  const vignette = 0.2 * (1 - span(t, plan.closer.at, 2));
  return {
    pose,
    travel: {zoom, center: [0.5, 0.5], smear: Math.hypot(...smear) < 0.0008 ? [0, 0] : smear, warp: 0, burn: 0, vignette, time: t * 0.25, ...now.travel},
  };
};
