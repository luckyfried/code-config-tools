// The reel's one camera: a station at every moment's card (the card's print filling the picture) held the card's own
// way, turning about the print so its field and its words slide apart, a move between stations that draws back before
// it goes, pulls back, banks and looks ahead along the walk and runs a little past its landing before it settles, and
// the closer's framing of the wall of the month's posts, square on, it settles into exactly, still from the board's stop.
import * as THREE from 'three';
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, mixPt, span, type Pt} from '../../system/three/motion';
import type {Travel} from '../../system/three/travel';
import {fxAt, nudgeAt, type Timeline} from '../../system/moves/layer';
import type {Look, Nudge} from '../../system/moves/types';
import {BACK, FOV, liftOf, MOVE, movesOf, PRINT, windAt, type Card, type Reel} from './plan';

/** What the camera frames: a wall point at the middle of the picture, `h` wall px tall at depth `z`, and how it is turned. */
export type Framing = {c: Pt; h: number; z: number; fov: number; yaw: number; pitch: number; roll: number};

export const poseOf = (r: Reel, f: Framing): Pose => {
  const target: [number, number, number] = [f.c[0] - r.W / 2, r.H / 2 - f.c[1], f.z];
  const D = f.h / 2 / Math.tan((f.fov * Math.PI) / 360);
  const cp = Math.cos(f.pitch);
  return {
    position: [target[0] + D * Math.sin(f.yaw) * cp, target[1] - D * Math.sin(f.pitch), target[2] + D * Math.cos(f.yaw) * cp],
    target, roll: f.roll, fov: f.fov,
  };
};

export const HOLD_FOV = FOV;

const stationOf = (r: Reel, c: Card): Framing => {
  const s = c.T.s;
  return {c: [c.T.o[0] + (s * r.W) / 2, c.T.o[1] + (s * r.H) / 2], h: r.H * s, z: liftOf(s) + PRINT * s, fov: HOLD_FOV, yaw: 0, pitch: 0, roll: 0};
};
// how much further in the camera drifts over the closer before it stops
const DRIFT = 0.03;
// the wall of the month's posts seen square on: its top row, the line and the closer's words under its foot, inside the
// safe area through the drift, their middle on the safe area's middle
const closerFraming = (r: Reel): Framing => {
  const {safe: s, W, H} = r;
  const top = r.closer.top - 50;
  const foot = Math.max(...r.closer.lines.map((l) => l.y)) + 40;
  const wide = ((r.closer.rule[1] - r.closer.rule[0] + 60) * H) / (W - s.left - s.right);
  const tall = ((foot - top) * H) / (H - s.top - s.bottom);
  const h = Math.max(wide, tall) / (1 - DRIFT);
  return {c: [W / 2, (top + foot) / 2 + ((s.bottom - s.top) / 2) * (h / H)], h, z: 30, fov: 34, yaw: 0, pitch: 0, roll: 0};
};

const mixF = (a: Framing, b: Framing, u: number): Framing => ({
  c: mixPt(a.c, b.c, u), h: a.h * Math.pow(b.h / a.h, u), z: lerp(a.z, b.z, u), fov: lerp(a.fov, b.fov, u),
  yaw: lerp(a.yaw, b.yaw, u), pitch: lerp(a.pitch, b.pitch, u), roll: lerp(a.roll, b.roll, u),
});

/** A move from `a` to `b` at eased progress `u`: it pulls back by `arc` at its middle, banks and looks ahead along the travel. */
const travel = (a: Framing, b: Framing, u: number, arc: number): Framing => {
  const m = mixF(a, b, u);
  const bell = Math.sin(Math.PI * u);
  const scale = Math.max(a.h, b.h);
  const lx = Math.max(-1, Math.min(1, (b.c[0] - a.c[0]) / scale));
  const ly = Math.max(-1, Math.min(1, (b.c[1] - a.c[1]) / scale));
  return {...m, h: m.h * (1 + arc * bell), yaw: m.yaw - 0.42 * lx * bell, pitch: m.pitch - 0.3 * ly * bell, roll: m.roll + 0.1 * lx * bell + 0.05 * bell};
};

const HOLD = bezier([0.35, 0, 0.65, 0.9]);
/** How far a hold turns about the print, radians each way: the field behind it and the words in front of it slide
 * apart by about their depth times this. */
const TURN = 0.22;

/** A hold on a card's station from `from` to `to`, the card's own way, each turning about the print: a push in to the
 * reel's `zoom` swinging from the card's right to its left, a pull back from it swinging from the left to the right and
 * rising, or a crane at that zoom rising from the card's foot toward its head while it tips from looking up to looking
 * down. A push or a pull stays centered on the card and a crane moves no further than the zoom's margin, so no hold
 * carries a word out of the safe area. */
const hold = (r: Reel, st: Framing, t: number, from: number, to: number, c: Card): Framing => {
  const k = HOLD(clamp01((t - from) / Math.max(0.1, to - from)));
  const swing = TURN * (1 - 2 * k);
  if (c.hold === 'crane') {
    const h = st.h / r.zoom;
    const margin = (st.h - h) / 2;
    return {...st, c: [st.c[0], st.c[1] + margin * (1 - 2 * k)], h, pitch: swing};
  }
  if (c.hold === 'push') return {...st, h: st.h / lerp(1, r.zoom, k), yaw: swing};
  return {...st, h: st.h / lerp(r.zoom, 1, k), yaw: -swing, pitch: 0.5 * swing};
};

/** `f` wound up against the move from `a` to `b` by `w` (0 to 1): drawn back along the way, and in or out against the
 * change of scale. */
const wound = (f: Framing, a: Framing, b: Framing, w: number): Framing => {
  if (w <= 0) return f;
  const reach = Math.min(0.12 * a.h, BACK * Math.hypot(b.c[0] - a.c[0], b.c[1] - a.c[1]));
  const far = Math.hypot(b.c[0] - a.c[0], b.c[1] - a.c[1]) || 1;
  const k = w * reach / far;
  return {...f, c: [f.c[0] - k * (b.c[0] - a.c[0]), f.c[1] - k * (b.c[1] - a.c[1])], h: f.h * Math.pow(b.h / a.h, -BACK * w)};
};

export const framingAt = (r: Reel, t: number): Framing => {
  const still = r.closer.still;
  t = Math.min(t, still);
  const cs = r.cards;
  const moves = movesOf(r);
  const stations = [...cs.map((c) => stationOf(r, c)), closerFraming(r)];
  const holdAt = (i: number, tt: number) => hold(r, stations[i], tt, i === 0 ? 0 : moves[i - 1].b, moves[i].a, cs[i]);
  // where the move after hold `i` goes: the next hold's start, or the closer's framing
  const toOf = (i: number) => (i === moves.length - 1 ? stations[i + 1] : holdAt(i + 1, moves[i].b));
  // hold `i` at `tt`, wound up against its move over the hold's last WINDUP beats
  const heldAt = (i: number, tt: number) => wound(holdAt(i, tt), holdAt(i, moves[i].a), toOf(i), windAt(r, i, tt));
  for (let i = 0; i < moves.length; i++) {
    const m = moves[i];
    if (t < m.a) return heldAt(i, t);
    if (t < m.b) {
      // from where this hold's wind-up leaves the camera to where the next begins
      const a = heldAt(i, m.a);
      const last = i === moves.length - 1;
      const b = toOf(i);
      const far = Math.hypot(b.c[0] - a.c[0], b.c[1] - a.c[1]) / Math.max(a.h, b.h);
      return travel(a, b, MOVE(clamp01((t - m.a) / (m.b - m.a))), (last ? 0.12 : 0.15) + 0.3 * Math.min(1, far));
    }
  }
  const end = closerFraming(r);
  const C = moves[moves.length - 1].b;
  // after the land the camera keeps drifting round the wall until the stop, where it stops dead with the music
  const drift = span(t, C, Math.max(0.5, still - C), bezier([0.2, 0.6, 0.3, 1]));
  return {...end, h: end.h * (1 - DRIFT * drift)};
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

/** `f` turned by a beat's move: its framed height scaled, its middle moved by shares of that height, rolled. */
const nudged = (f: Framing, n: Nudge): Framing => ({
  ...f, h: f.h * (n.scale ?? 1), c: [f.c[0] + (n.dx ?? 0) * f.h, f.c[1] + (n.dy ?? 0) * f.h], roll: f.roll + (n.roll ?? 0),
});

/** The pose at beat `t` and the travel pass for it: the camera's framing as the beat's move turns it, the blur of the
 * move the shutter saw over the last half frame, the vignette, and what the beat's move and the cut playing add. The
 * picture holds still from the board's stop. */
export const shotAt = (r: Reel, t: number, pulse: number, line: Timeline, look: Look): {pose: Pose; travel: Travel} => {
  const at = (tt: number) => nudged(framingAt(r, tt), nudgeAt(line, look, Math.min(tt, r.closer.still)));
  const pose = poseOf(r, at(t));
  const prev = poseOf(r, at(t - 0.5 / pulse));
  const aspect = r.W / r.H;
  const p = new THREE.Vector3(...pose.target);
  setCam(prev, aspect);
  const a = p.clone().project(cam);
  setCam(pose, aspect);
  const b = p.clone().project(cam);
  const cap = (v: number, m: number) => Math.max(-m, Math.min(m, v));
  const smear: [number, number] = [cap((b.x - a.x) * 0.5, 0.09), cap((b.y - a.y) * 0.5, 0.09)];
  const vignette = 0.2 * (1 - span(t, r.closer.at, 2));
  return {
    pose,
    travel: {zoom: 0, center: [0.5, 0.5], smear: Math.hypot(...smear) < 0.0008 ? [0, 0] : smear, warp: 0, burn: 0, vignette,
      time: Math.min(t, r.closer.still) * 0.25, ...fxAt(line, look, Math.min(t, r.closer.still))},
  };
};
