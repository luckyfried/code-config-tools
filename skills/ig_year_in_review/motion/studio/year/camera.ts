// The year film's one camera: the hook framed on the title over its open window, a dive into the window and out of it
// to the first month's piece frame, then each month in turn filling the picture while the camera pushes slowly in
// about its subject and the month's move (the card's, picked for what the photograph shows) turns the framing, so the
// photograph's two layers slide against each other. Into a month whose cut jumps, the camera holds on the month before
// to the moment of the cut and is on the new month from that frame; into one whose cut travels, it draws back off the
// month, so the print shows whole on its field, while the next month's photograph opens over it, then pushes into the
// next, past its mark and back. From the last month a pull back to the wall, where it comes to rest. Every move between
// two framings gathers itself, overshoots its mark a little and settles.
import * as THREE from 'three';
import {cutOf} from '../../system/moves';
import {fxAt, nudgeAt} from '../../system/moves/layer';
import type {Nudge} from '../../system/moves/types';
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, mixPt, span, type Pt} from '../../system/three/motion';
import type {Travel} from '../../system/three/travel';
import {openingOf} from './month';
import {HOLD_FOV, layerOf, liftOf, onWall, world, type Box, type Month, type Plan} from './plan';

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

const CLOSER_FOV = 18;

const still = (c: Pt, h: number, z = 0, fov = HOLD_FOV): Framing => ({c, h, z, fov, yaw: 0, pitch: 0, roll: 0});

/** The film's first framing: the year's underline across the picture's middle, above the caption's band, and the
 * whole heading (the bounds headingSeen reads) inside the picture, so the year shows as it slams in. */
const hookOf = (plan: Plan): Framing => {
  const [x0, , x1] = plan.heading;
  const h = Math.max(1100, ((x1 - x0 + 40) * plan.H) / plan.W);
  return still([x0 - 20 + (h * plan.W) / plan.H / 2, plan.rule[1]], h);
};

/** How far inside its piece frame a month's station frames, as a share of the frame: room for the stage's lean, which
 * turns the picture's corners a few pixels into a sideways move (system/three/Stage.tsx), and for the overshoot of the
 * push into the month. */
export const ROOM = 0.025;

/** How far the camera draws back off a month before the next one: the picture this many times the piece frame's height,
 * so the print stands whole inside it on its field, its shadow under it. */
export const BACK = 1.45;
/** A cut that jumps: the camera eases back by GATHER over the last ANTICIPATE beats before it, and the month it cuts to
 * lands LAND_TIGHT tight and settles on its mark over SETTLE beats. */
export const GATHER = 0.035;
export const ANTICIPATE = 0.5;
export const LAND_TIGHT = 0.06;
export const SETTLE = 0.6;

/** The framing that shows month `m`'s piece frame: a full frame `ROOM` in from its edges, through a longer lens from
 * the place that frames it whole, so the hand never shows past its photograph and the two layers still line up from
 * there; a picture in the card's box exactly, so it stands in the frame where the card's grid and its moves' mats put
 * it. */
export const stationOf = (plan: Plan, m: Month): Framing => {
  const s = m.T.s;
  const room = m.full ? ROOM : 0;
  const fov = (360 / Math.PI) * Math.atan((1 - room) * Math.tan((HOLD_FOV * Math.PI) / 360));
  return still([m.T.o[0] + (s * plan.W) / 2, m.T.o[1] + (s * plan.H) / 2], plan.H * s * (1 - room), liftOf(m), fov);
};

/** Inside the hook's window: its photographs fill the picture, edge to edge. */
const windowOf = (plan: Plan): Framing => {
  const [x0, y0, x1, y1] = plan.hook.window;
  return still([(x0 + x1) / 2, (y0 + y1) / 2], (y1 - y0) * 0.97);
};

const closerOf = (plan: Plan): Framing => still([plan.W / 2, plan.H / 2], plan.H, 0, CLOSER_FOV);

const mixF = (a: Framing, b: Framing, u: number): Framing => ({
  c: mixPt(a.c, b.c, u), h: a.h * Math.pow(b.h / a.h, u), z: lerp(a.z, b.z, u), fov: lerp(a.fov, b.fov, u),
  yaw: lerp(a.yaw, b.yaw, u), pitch: lerp(a.pitch, b.pitch, u), roll: lerp(a.roll, b.roll, u),
});

/** A move from `a` to `b` at progress `u` (already eased): it pulls back by `arc` at its middle, banks and looks ahead along the travel. */
const travel = (a: Framing, b: Framing, u: number, arc: number): Framing => {
  const m = mixF(a, b, u);
  const bell = Math.sin(Math.PI * u);
  const scale = Math.max(a.h, b.h);
  const lx = Math.max(-1, Math.min(1, (b.c[0] - a.c[0]) / scale));
  const ly = Math.max(-1, Math.min(1, (b.c[1] - a.c[1]) / scale));
  return {...m, h: m.h * (1 + arc * bell), yaw: m.yaw - 0.42 * lx * bell, pitch: m.pitch - 0.3 * ly * bell, roll: m.roll + 0.1 * lx * bell, fov: m.fov + 10 * bell};
};

export type Shot = {framing: Framing; travel: Partial<Travel>};

/** A framing turned by a move's nudge: its height scaled, its middle moved by shares of that height, rolled. */
const nudged = (f: Framing, n: Nudge): Framing => {
  const h = f.h * (n.scale ?? 1);
  return {...f, h, c: [f.c[0] + (n.dx ?? 0) * h, f.c[1] + (n.dy ?? 0) * h], roll: f.roll + (n.roll ?? 0)};
};

/** The camera over a month's hold, from its arrival until the month is left: on a full frame a slow push in about the
 * photograph's focus (4%, 7% on the story's peak), drifting a little to the side as it goes. The camera turns about the
 * near layer, which carries the month's words, so the words hold their place in the picture while the photograph under
 * the line slides behind them. A picture in the card's box holds still in it, so the card's grid and the mats and cells
 * of its moves lie exactly on its box, and the photograph pushes in inside the box (`month.tsx`). */
const held = (plan: Plan, m: Month, t: number): Framing => {
  const st = stationOf(plan, m);
  const near = layerOf(plan, m, t);
  const nk = near.T.s / m.T.s;
  const hold = bezier([0.3, 0, 0.6, 1])(clamp01((t - m.at.arrive) / Math.max(0.1, m.at.pull[0] - m.at.arrive)));
  const [px, py, pw, ph] = m.place;
  const f = onWall(near.T, [Math.min(0.8, Math.max(0.2, (px + m.focus[0] * pw) / plan.W)) * plan.W, Math.min(0.8, Math.max(0.2, (py + m.focus[1] * ph) / plan.H)) * plan.H]);
  const still = !m.full;
  const k = still ? 1 : 1 - (m.peak ? 0.07 : 0.04) * hold;
  // across a cut that jumps, the camera gathers itself, easing back a little over the last ANTICIPATE beats, and the
  // next month lands a touch tight, runs past its mark and settles on it over SETTLE beats
  const i = plan.months.indexOf(m);
  const next = plan.months[i + 1];
  const gathered = !still && next && jumpsInto(plan, i + 1) ? 1 + GATHER * bezier([0.4, 0, 0.7, 1])(clamp01((t - next.start + ANTICIPATE) / ANTICIPATE)) : 1;
  const landing = !still && jumpsInto(plan, i) ? 1 - LAND_TIGHT * (1 - bezier([0.2, 0.8, 0.3, 1.25])(clamp01((t - m.start) / SETTLE))) : 1;
  // the drift turns one way and the next month's the other, so the layers slide a new way each month
  const sign = m.month % 2 ? 1 : -1;
  return {...st, c: mixPt(f, st.c, k), h: st.h * nk * k * gathered * landing, z: near.z, yaw: still ? 0 : sign * 0.05 * hold};
};

/** Whether the cut into month `i` jumps: the picture is the month before to the moment of the cut, then this one. The
 * hook's montage always cuts into the first month. */
export const jumpsInto = (plan: Plan, i: number) => i === 0 || Boolean(cutOf(plan.months[i].transition ?? undefined)?.jump);

/** The camera's framing at beat `t`, turned by the beat's move, and what the move and the cut playing add to the
 * travel pass. */
export const framingAt = (plan: Plan, t: number): Shot => {
  const base = baseAt(plan, t);
  return {framing: nudged(base.framing, nudgeAt(plan.line, plan.look, t)), travel: {...base.travel, ...fxAt(plan.line, plan.look, t)}};
};

/** The camera's framing at beat `t`, before the beat's move turns it. */
const baseAt = (plan: Plan, t: number): Shot => {
  const move = bezier(plan.ease.move);
  // a move between two framings gathers itself, overshoots its mark a little and settles; a draw back eases out and
  // slows to a stop, ready to push
  const glide = bezier([0.45, -0.18, 0.3, 1.1]);
  const gather = bezier([0.3, 0, 0.25, 1]);
  const months = plan.months;
  const first = months[0];
  const hook = hookOf(plan);
  const inside = windowOf(plan);
  const pushed = (u: number): Framing => ({...inside, h: inside.h * (1 - 0.05 * u)});
  if (t < first.start) {
    // the title enters on the first month's photograph and the underline drops open into the window under it, the
    // months flashing in it; the camera holds on the year over its window, then dives in and pushes while they flash
    const open = 1 + 0.1 * (1 - span(t, 0, 0.4, bezier([0.2, 0.9, 0.3, 1])));
    const wall = {...hook, h: hook.h * open};
    const [d0, dl] = plan.hook.dive;
    const into = span(t, d0, dl, move);
    const push = pushed(clamp01((t - d0) / Math.max(0.1, first.start - d0)));
    return {framing: into < 1 ? travel(wall, push, into, 0.04) : push, travel: {}};
  }
  for (let i = 0; i < months.length; i++) {
    const m = months[i];
    const next = months[i + 1];
    const [p0] = m.at.pull;
    if (t < p0) return {framing: held(plan, m, t), travel: {}};
    if (next && jumpsInto(plan, i + 1)) {
      // a cut that jumps: the camera stays on the month to the moment of the cut, and is on the next one from there
      if (t < next.start) return {framing: held(plan, m, t), travel: {}};
      continue;
    }
    if (next) {
      // the camera draws back off the month, slowing as the print comes whole into the picture on its field while the
      // next month's photograph opens over it, then pushes into the next one, past its mark and back
      const [o0] = openingOf(plan, i + 1);
      const back = {...held(plan, m, p0), h: stationOf(plan, m).h * BACK};
      if (t < o0) return {framing: mixF(held(plan, m, p0), back, gather(clamp01((t - p0) / Math.max(0.1, o0 - p0)))), travel: {}};
      if (t < next.at.arrive) return {framing: mixF(back, stationOf(plan, next), glide(clamp01((t - o0) / (next.at.arrive - o0)))), travel: {}};
      continue;
    }
    // the last month: the camera pulls back from it to the whole wall as its halves close and its line slides into its
    // row, square to the wall so the year's names stay in the picture
    const end = closerOf(plan);
    const C = plan.closer.at + 0.6;
    if (t < C) {
      const u = glide(clamp01((t - p0) / (C - p0)));
      return {framing: mixF(held(plan, m, p0), end, u), travel: {}};
    }
    // the whole wall keeps pushing in over the dot's hops and comes to rest at its stop
    return {framing: {...end, h: end.h * (1 - 0.03 * span(t, C, plan.closer.still - C))}, travel: {}};
  }
  return {framing: closerOf(plan), travel: {}};
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

/** Whether a box on the wall at height `z` shows at beat `t`: 1 while it lies wholly inside the picture, 0 from the
 * frame the picture's edge reaches it, so it is seen whole or not at all and never cut or seen through. */
const seenOf = (plan: Plan, t: number, [x0, y0, x1, y1]: Box, z: number) => {
  setCam(poseOf(plan, framingAt(plan, t).framing), plan.W / plan.H);
  const corners: Pt[] = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
  const inside = corners.every((p) => {
    const v = world(plan, p, z).project(cam);
    return Math.abs(v.x) <= 1 && Math.abs(v.y) <= 1;
  });
  return inside ? 1 : 0;
};

/** Whether the year's heading shows at beat `t`. */
export const headingSeen = (plan: Plan, t: number) => seenOf(plan, t, plan.heading, 1);

/** The pose at beat `t` and the finishing pass for it: the sideways blur of the move the shutter saw over the last half
 * frame (a push or a pull stays sharp, and so does a cut that jumps), and what the beat's move and the cut add. The
 * grade reaches the frame through the stage's `grade`, the vignette and the rest of the finish through the card. */
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
  const cut = plan.months.some((m, i) => jumpsInto(plan, i) && m.start > t - half && m.start <= t);
  const smear: [number, number] = cut ? [0, 0] : [cap((b.x - a.x) * 0.5, 0.03), cap((b.y - a.y) * 0.5, 0.03)];
  return {
    pose,
    travel: {
      zoom: 0, center: [0.5, 0.5], smear: Math.hypot(...smear) < 0.0008 ? [0, 0] : smear, warp: 0, burn: 0, vignette: 0,
      time: t * 0.25, ...now.travel,
    },
  };
};

/** Where world point `p` falls in the picture at beat `t`, in frame px. */
export const screenOf = (plan: Plan, t: number, p: THREE.Vector3): Pt => {
  setCam(shotAt(plan, t).pose, plan.W / plan.H);
  const v = p.clone().project(cam);
  return [((v.x + 1) / 2) * plan.W, ((1 - v.y) / 2) * plan.H];
};

/** The world point at height `z` that the picture at beat `t` shows at frame point `q`. */
export const wallUnder = (plan: Plan, t: number, q: Pt, z: number) => {
  setCam(shotAt(plan, t).pose, plan.W / plan.H);
  const d = new THREE.Vector3((q[0] / plan.W) * 2 - 1, 1 - (q[1] / plan.H) * 2, 0.5).unproject(cam).sub(cam.position).normalize();
  return cam.position.clone().addScaledVector(d, (z - cam.position.z) / d.z);
};
