// The drive film's one camera: a station at every card (the card's piece frame filling the picture, pushing in toward
// the person its tag points at, turned by the beat's move as the style card names it), a jump at every cut with the
// style's cut playing over it, and on the closer a push that settles onto the head of the wall as the impact lands,
// then the move down the wall with the tag that widens into the closer's framing, the wall's foot, exactly as the tag
// lands on the last. The picture steps at the card's cadence; from the still on, nothing moves.
import * as THREE from 'three';
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, mixPt, span, type Pt} from '../../system/three/motion';
import type {Travel} from '../../system/three/travel';
import {fxAt, nudgeAt} from '../../system/moves/layer';
import type {Nudge} from '../../system/moves/types';
import {onWall, type Card, type Plan} from './plan';
import {cardScale, liftOf, typeZ} from './card';

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

/** Where on the wall the card's camera pushes toward: the point its tag (on the hook, all its tags) points at. */
export const aimOf = (c: Card): Pt => {
  if (!c.tags.length) return onWall(c.T, [c.place[0] + c.place[2] / 2, c.place[1] + c.place[3] / 2]);
  const ps = c.tags.map((t) => onWall(c.T, t.tip));
  return [ps.reduce((a, p) => a + p[0], 0) / ps.length, ps.reduce((a, p) => a + p[1], 0) / ps.length];
};
const PUSH = 0.12;
const TOWARD = 0.28;
const tanHalf = (fov: number) => Math.tan((fov * Math.PI) / 360);

/** The framing that shows card `c`'s piece frame whole. */
export const stationOf = (plan: Plan, c: Card): Framing => {
  const s = cardScale(c);
  return {c: [c.T.o[0] + s * plan.W / 2, c.T.o[1] + s * plan.H / 2], h: plan.H * s, z: liftOf(c), fov: HOLD_FOV, yaw: 0, pitch: 0, roll: 0};
};

const fit = (v: number, lo: number, hi: number) => (lo <= hi ? Math.min(hi, Math.max(lo, v)) : (lo + hi) / 2);

/** The middles a framing `h` tall can take with the picture on card `c`'s photograph, which ends at its place (on a
 * paper card the paper over the edge is picture too, from the frame's top): x from, x to, y from, y to. */
const onPhoto = (plan: Plan, c: Card, h: number) => {
  const [x0, y0] = onWall(c.T, [c.place[0], c.field === 'photo' ? c.place[1] : Math.min(0, c.place[1])]);
  const [x1, y1] = onWall(c.T, [c.place[0] + c.place[2], c.place[1] + c.place[3]]);
  const hw = (h * plan.W) / plan.H / 2;
  return [x0 + hw, x1 - hw, y0 + h / 2, y1 - h / 2];
};

/** Card `c` held at `hold` (0 on arrival, 1 at the cut): pushed in PUSH and moved TOWARD of the way to its aim, turned
 * by the beat's move `n`, then eased back (never past the station, unless its type leaves the push no room, when the
 * camera pulls back PUSH instead) and moved over just enough that the picture stays on the photograph and
 * that its type and tags, at their depth in front of the photograph, stay inside the format's safe area as the lens sees
 * them. board_drive lays a card's type inside the safe area as the lens sees it from the station, where both hold. */
export const heldOf = (plan: Plan, c: Card, hold: number, n: Nudge = {}): Framing => {
  const st0 = stationOf(plan, c);
  const st = {...st0, roll: n.roll ?? 0};
  const h0 = Math.min(st.h, st.h * (1 - PUSH * hold) * (n.scale ?? 1));
  const c0 = mixPt(st.c, aimOf(c), TOWARD * hold);
  const want = {c: [c0[0] + (n.dx ?? 0) * h0, c0[1] + (n.dy ?? 0) * h0] as Pt, h: h0};
  if (!c.keep) {
    const [ax, bx, ay, by] = onPhoto(plan, c, want.h);
    return {...st, h: want.h, c: [fit(want.c[0], ax, bx), fit(want.c[1], ay, by)]};
  }
  // a point dz nearer the lens than the framed plane is drawn at k picture px per wall px
  const near = 2 * (typeZ(c) - liftOf(c)) * tanHalf(st.fov);
  const [L, T, R, B] = plan.safe;
  const [x0, y0] = onWall(c.T, [c.keep[0], c.keep[1]]);
  const [x1, y1] = onWall(c.T, [c.keep[2], c.keep[3]]);
  // the narrowest framing that keeps the type inside the safe area
  const least = plan.H / Math.min((R - L) / (x1 - x0), (B - T) / (y1 - y0)) + near;
  // type that leaves the push under half its way in turns it round: the camera eases back from the station, as far
  // as the photograph still fills the picture; otherwise it pushes in, never wider than the station
  const [px0, px1, py0, py1] = onPhoto(plan, c, 0);
  const widest = Math.min(((px1 - px0) * plan.H) / plan.W, py1 - py0);
  const h = least > st.h * (1 - PUSH / 2)
    ? Math.max(st.h, Math.min(widest, st.h * (1 + PUSH * hold)))
    : Math.min(st.h, Math.max(want.h, least));
  const k = plan.H / (h - near);
  const [ax, bx, ay, by] = onPhoto(plan, c, h);
  return {
    ...st, h,
    c: [fit(want.c[0], Math.max(ax, x1 - (R - plan.W / 2) / k), Math.min(bx, x0 + (plan.W / 2 - L) / k)),
      fit(want.c[1], Math.max(ay, y1 - (B - plan.H / 2) / k), Math.min(by, y0 + (plan.H / 2 - T) / k))],
  };
};

/** The closer's framing: the foot of the wall, a frame tall, where the last person, the handle and the title stand. */
const closerFraming = (plan: Plan): Framing => ({c: [plan.W / 2, plan.closer.height - plan.H / 2], h: plan.H, z: 0, fov: CLOSER_FOV, yaw: 0, pitch: 0, roll: 0});
/** The head of the closer's wall, where the tag starts its run: the top HEAD of a frame of the wall filling the picture,
 * wide enough that the stamps hanging at the wall's sides stay whole in it. */
const HEAD = 0.9;
const headFraming = (plan: Plan): Framing => ({...closerFraming(plan), c: [plan.W / 2, (plan.H * HEAD) / 2], h: plan.H * HEAD});

const mixF = (a: Framing, b: Framing, u: number): Framing => ({
  c: mixPt(a.c, b.c, u), h: a.h * Math.pow(b.h / a.h, u), z: lerp(a.z, b.z, u), fov: lerp(a.fov, b.fov, u),
  yaw: lerp(a.yaw, b.yaw, u), pitch: lerp(a.pitch, b.pitch, u), roll: lerp(a.roll, b.roll, u),
});

/** How far through its hold card `i` is at beat `t`: 0 as it arrives, 1 at the cut to the next beat. */
export const holdAt = (plan: Plan, i: number, t: number) => {
  const c = plan.cards[i];
  return clamp01((t - c.arrive) / Math.max(0.1, c.leave - c.arrive));
};

/** Card `i` held at beat `t`, with the beat's move turning the camera while the card is the one on screen. */
export const heldAt = (plan: Plan, i: number, t: number): Framing => {
  const c = plan.cards[i];
  const on = t >= c.arrive && t < c.leave;
  return heldOf(plan, c, holdAt(plan, i, t), on ? nudgeAt(plan.line, plan.look, t) : {});
};

export type Shot = {framing: Framing; travel: Partial<Travel>};

/** The camera's framing at beat `t`. Each card holds from its arrival to the cut into the next beat, and the camera
 * jumps there: the style's cut plays over the jump. On the closer the camera opens pushed in on the head of the wall and
 * settles onto it as the impact lands, runs down the wall with the tag, widening onto the wall's foot as the tag lands
 * on the last, and holds there. */
export const framingAt = (plan: Plan, t: number): Shot => {
  const cards = plan.cards;
  if (t < plan.closer.at) {
    let i = cards.length - 1;
    while (i > 0 && t < cards[i].arrive) i--;
    const f = heldAt(plan, i, t);
    // the hook opens a touch wide and settles in, so the film starts moving on its first frame
    const open = i === 0 ? 1 + 0.12 * (1 - span(t, 0, 0.6, bezier(plan.ease.enter))) : 1;
    return {framing: {...f, h: f.h * open}, travel: {}};
  }
  const head = headFraming(plan);
  const end = closerFraming(plan);
  const R = plan.closer.route;
  if (t < R.at) {
    const u = span(t, plan.closer.at, Math.max(0.1, R.at - plan.closer.at), bezier([0.2, 0.9, 0.3, 1.08]));
    return {framing: mixF({...head, h: head.h * 0.86}, head, u), travel: {}};
  }
  const down = span(t, R.at, Math.max(0.5, R.len), bezier(plan.closer.height > plan.H ? [0.3, 0, 0.65, 1] : [0.45, 0, 0.25, 1]));
  return {framing: mixF(head, end, down), travel: {}};
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

/** Which held shot beat `t` is in: the cards in turn, then the closer. */
const segOf = (plan: Plan, t: number) => plan.cards.filter((c) => t >= c.arrive).length + (t >= plan.closer.at ? 1 : 0);

/** The pose at beat `t` and the travel pass for it: the blur of the move the shutter saw over the last half frame and what the beat's move and cut add; the card's finish does the rest. */
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
  // a cut is a jump: the shutter never sees the camera cross it, so the frame after a cut is as sharp as any other
  const jumped = segOf(plan, t) !== segOf(plan, t - half);
  const smear: [number, number] = jumped ? [0, 0] : [cap((b.x - a.x) * 0.5, 0.09), cap((b.y - a.y) * 0.5, 0.09)];
  // a push or a pull blurs a little along its rays; the travel across the wall is the smear's
  const zoom = jumped ? 0 : Math.min(0.05, Math.abs(Math.log(was.framing.h / now.framing.h)) * 0.8);
  // the operator's hand holds still from the still on, as the picture does
  return {
    pose,
    travel: {zoom, center: [0.5, 0.5], smear: Math.hypot(...smear) < 0.0008 ? [0, 0] : smear, warp: 0, burn: 0, vignette: 0,
      time: Math.min(t, plan.closer.still) * 0.25, ...now.travel, ...fxAt(plan.line, plan.look, Math.min(t, plan.closer.still))},
  };
};
