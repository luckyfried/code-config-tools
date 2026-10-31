// The drive film's one camera, from the board's keys: a framing per key, a move between two keys on the key's own
// curve (a camera settling on a framing starts a touch the other way and settles a touch past it) that pulls back by
// the key's arc at its middle, banks and looks ahead along the travel, and the extra treatment a key asks of
// the move into it; over a beat whose words the board did not lay against the camera (the wall, a post the frame does
// not hold) the card's move for the beat turns the framing, and the beat's move and cut add to the travel pass.
import * as THREE from 'three';
import {beatAt, fxAt, nudgeAt, type Timeline} from '../../system/moves/layer';
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, mixPt} from '../../system/three/motion';
import type {Travel} from '../../system/three/travel';
import {toWorld, type Framing, type Plan} from './plan';
import {cornersOf} from './quad';

/** Beats of the music at board beat `t`. */
export const musicAt = (plan: Plan, t: number) => (t * plan.pulse) / plan.look.pulse;

/** Whether the card's move may turn the camera at board beat `t`: on the wall after its title, and on a post the frame
 * does not hold, never where the board set words against a camera at rest. */
const turns = (plan: Plan, t: number) => {
  const p = beatAt(plan.timeline, plan.look, musicAt(plan, t));
  if (!p) return false;
  if (p.beat.form === 'wall') return true;
  if (p.beat.form !== 'photo') return false;
  return !plan.posts.find((q) => q.beat === p.beat.id)?.full;
};

const nudged = (plan: Plan, f: Framing, t: number): Framing => {
  if (!turns(plan, t)) return f;
  const n = nudgeAt(plan.timeline, plan.look, musicAt(plan, t));
  return {...f, h: f.h * (n.scale ?? 1), c: [f.c[0] + (n.dx ?? 0) * f.h, f.c[1] + (n.dy ?? 0) * f.h], roll: f.roll + (n.roll ?? 0)};
};

export const poseOf = (plan: Plan, f: Framing): Pose => {
  const target: [number, number, number] = [f.c[0] - plan.W / 2, plan.H / 2 - f.c[1], f.z];
  const D = f.h / 2 / Math.tan((f.fov * Math.PI) / 360);
  const cp = Math.cos(f.pitch);
  return {
    position: [target[0] + D * Math.sin(f.yaw) * cp, target[1] - D * Math.sin(f.pitch), target[2] + D * Math.cos(f.yaw) * cp],
    target, roll: f.roll, fov: f.fov,
  };
};

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
  return {...m, h: m.h * (1 + arc * bell), yaw: m.yaw - 0.42 * lx * bell, pitch: m.pitch - 0.3 * ly * bell, roll: m.roll + 0.1 * lx * bell, fov: m.fov + 10 * arc * bell};
};

export type Shot = {framing: Framing; travel: Partial<Travel>};

export const framingAt = (plan: Plan, t: number): Shot => {
  const keys = plan.camera;
  const move = bezier(plan.ease.move);
  if (t <= keys[0].t) return {framing: keys[0], travel: {}};
  for (let i = 0; i + 1 < keys.length; i++) {
    const a = keys[i], b = keys[i + 1];
    if (t > b.t) continue;
    const raw = clamp01((t - a.t) / Math.max(1e-6, b.t - a.t));
    const u = b.ease ? bezier(b.ease)(raw) : move(raw);
    const f = b.arc > 0 ? travel(a, b, u, b.arc) : mixF(a, b, u);
    const bell = Math.sin(Math.PI * raw);
    return {framing: f, travel: {warp: (b.travel?.warp ?? 0) * bell, burn: (b.travel?.burn ?? 0) * bell}};
  }
  return {framing: keys[keys.length - 1], travel: {}};
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
  const was = framingAt(plan, t - 0.5 / plan.pulse);
  const pose = poseOf(plan, nudged(plan, now.framing, t));
  const prev = poseOf(plan, nudged(plan, was.framing, t - 0.5 / plan.pulse));
  const aspect = plan.W / plan.H;
  const p = new THREE.Vector3(...pose.target);
  setCam(prev, aspect);
  const a = p.clone().project(cam);
  setCam(pose, aspect);
  const b = p.clone().project(cam);
  const cap = (v: number, m: number) => Math.max(-m, Math.min(m, v));
  const smear: [number, number] = [cap((b.x - a.x) * 0.5, 0.09), cap((b.y - a.y) * 0.5, 0.09)];
  // the radial blur of a push or a pull, capped so the fastest pull-back still reads as the picture it is leaving
  const zoom = Math.min(0.06, Math.abs(Math.log(was.framing.h / now.framing.h)) * 1.2);
  const fx = t < plan.closer.still ? fxAt(plan.timeline, plan.look, musicAt(plan, t)) : {};
  return {
    pose,
    travel: {zoom, center: [0.5, 0.5], smear: Math.hypot(...smear) < 0.0008 ? [0, 0] : smear, warp: 0, burn: 0, vignette: 0,
      // the camera's hand stops with the picture: its drift and sway are a function of this time
      time: Math.min(t, plan.closer.still) * 0.25,
      ...Object.fromEntries(Object.entries(now.travel).filter(([, v]) => v !== undefined)),
      ...Object.fromEntries(Object.entries(fx).filter(([, v]) => v !== undefined))} as Travel,
  };
};

/** Where world points stand on the screen under `pose`, as the box [x0, y0, x1, y1] px round them. */
const boxOn = (plan: Plan, pose: Pose, pts: THREE.Vector3[]): [number, number, number, number] => {
  setCam(pose, plan.W / plan.H);
  const xs: number[] = [], ys: number[] = [];
  for (const v of pts) {
    const q = v.clone().project(cam);
    xs.push(((q.x + 1) / 2) * plan.W);
    ys.push(((1 - q.y) / 2) * plan.H);
  }
  const r = (v: number) => Math.round(v * 10) / 10;
  return [r(Math.min(...xs)), r(Math.min(...ys)), r(Math.max(...xs)), r(Math.max(...ys))];
};

/** The film's beats as the card's moves read them: a photo beat (a post the frame holds) carries where its photograph
 * stands on the screen while the camera holds on it (`box`, the page's picture box) and the music's beats of the hold,
 * from the frame locking on the crop to the crop drawing back (`held`). A photo beat starts as the frame locks on the
 * crop, so its move draws on the photograph where the camera holds it and never on the way in; the beat before it runs
 * until then. The caption stands on the post's page, so a photo beat's move is handed no words and moves the picture
 * alone. */
export const timelineOf = (plan: Plan): Timeline => {
  const beats = plan.timeline.beats.map((b) => {
    if (b.form !== 'photo') return b;
    const p = plan.posts.find((q) => q.beat === b.id);
    if (!p) return {...b, words: '', label: ''};
    const from = p.times.close[0] + p.times.close[1], to = p.times.drop[0];
    const mid = (from + to) / 2;
    const pose = shotAt(plan, mid).pose;
    const box = boxOn(plan, pose, cornersOf(p.crop).map((q) => new THREE.Vector3(...toWorld(plan, q, p.z))));
    const held: [number, number] = [musicAt(plan, from), musicAt(plan, to)];
    return {...b, at: Math.max(b.at, held[0]), words: '', label: '', box, held};
  });
  return {...plan.timeline, beats, cuts: beats.map((b, i) => (b.held ? b.at : plan.timeline.cuts[i]))};
};
