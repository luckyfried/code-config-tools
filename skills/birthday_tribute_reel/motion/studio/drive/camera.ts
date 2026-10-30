// The year's one camera. At every card it holds on the print standing off the wall and arcs slowly about the
// photograph's subject as it closes in, so the wall, the far part of the picture, its subject and the type pass each
// other at their own rates. Into a card the style's cut either jumps (the camera holds to the moment of the cut and is on
// the next card from that frame) or travels, and a travel makes the move the next card's own arrival asks for: a slide
// along the wall at the card's own distance for a card that slides in, a swing that bows out, looks along the turn and
// banks into it for a card that hinges in, and a lift back off the wall that shows the cells around before it drops
// onto a card that rises or falls in. Each move first leans the other way, runs, and lands past the next card before it
// settles back. At the last card it pulls back onto the whole wall and lands on it as the cover slams; from there only
// the cover's slam and the last figure's punch move it, and from the stop it is still. Over all of it the beat's move
// from the style card turns the framing, and the move and the cut add to the travel pass.
import * as THREE from 'three';
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, mixPt, smooth, span, type Pt} from '../../system/three/motion';
import type {Travel} from '../../system/three/travel';
import {cutOf} from '../../system/moves';
import {fxAt, nudgeAt, type Timeline} from '../../system/moves/layer';
import type {Nudge} from '../../system/moves/types';
import {lookOf, type Card, type Plan} from './plan';
import {cardScale, liftOf, photoBoxOf} from './card';
import {onWall} from './plan';
import {COVER_Z} from './words';

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

/** The framing that shows card `c`'s frame whole. */
export const stationOf = (plan: Plan, c: Card): Framing => {
  const s = cardScale(c);
  return {c: [c.T.o[0] + s * plan.W / 2, c.T.o[1] + s * plan.H / 2], h: plan.H * s, z: liftOf(c), fov: HOLD_FOV, yaw: 0, pitch: 0, roll: 0};
};

/** A hold opens this much wider than the card's frame, the wall around the card in the picture, and closes in to TIGHT. */
const WIDE = 1.3;
const TIGHT = 1.12;
/** How far a hold arcs about the subject, in radians either way, and how far toward the subject it drifts. */
const ARC = 0.09;
const TOWARD = 0.25;

/** The framing of card `i`'s hold at progress `e` (eased): wide at its start and close at its end, turning toward the
 * side the photograph's subject stands on and drifting toward it as far as the frame stays in the picture; the hook
 * fills the frame. */
const holdOf = (plan: Plan, i: number, e: number): Framing => {
  const c = plan.cards[i];
  const st = stationOf(plan, c);
  if (c.hook) return st;
  const k = lerp(WIDE, TIGHT, e);
  const sub = onWall(c.T, [(c.subject[0] + c.subject[2]) / 2, (c.subject[1] + c.subject[3]) / 2]);
  const room = [((k - 1) / 2) * st.h * (plan.W / plan.H), ((k - 1) / 2) * st.h];
  const shift = [0, 1].map((j) => Math.max(-room[j], Math.min(room[j], (sub[j] - st.c[j]) * TOWARD * e)));
  const turn = sub[0] >= st.c[0] ? 1 : -1;
  return {...st, c: [st.c[0] + shift[0], st.c[1] + shift[1]], h: st.h * k, yaw: turn * ARC * (2 * e - 1), pitch: 0.03 * (2 * e - 1)};
};

/** A move between two framings. `lean` is how far it first goes the other way and `over` how far it lands past, both
 * shares of the travel; `dip` how far it closes in as it leans; `back` how far it widens at its middle; `bow` how far
 * its path bows off the straight line, a share of the travel; `look` how far it turns to look along the travel and
 * `bank` how far it rolls into it, radians. */
type Move = {lean: number; over: number; dip: number; back: number; bow: number; look: number; bank: number};
/** The moves between cards, each the one a card's arrival asks for: a slide along the wall for a card that slides in, a
 * swing that banks for one that hinges in, a lift back off the wall for one that rises or falls in. */
const SLIDE: Move = {lean: 0.1, over: 0.06, dip: 0, back: 0, bow: 0, look: 0.07, bank: 0};
const LIFT_OFF: Move = {lean: 0.03, over: 0.04, dip: 0.08, back: 0.9, bow: 0, look: 0, bank: 0};
const SWING: Move = {lean: 0.08, over: 0.06, dip: 0, back: 0.15, bow: 0.3, look: 0.3, bank: 0.12};
const moveInto = (c: Card): Move => (c.entry === 'slide' ? SLIDE : c.entry === 'hinge' ? SWING : LIFT_OFF);
/** The pull back from the last card onto the whole wall. */
const BACK: Move = {lean: 0.04, over: 0.03, dip: 0.04, back: 0, bow: 0.12, look: 0.12, bank: 0.04};
/** A move's anticipation peaks at A of its time and its overshoot at B. */
const A = 0.3;
const B = 0.82;
/** Beats before a card's leave its move starts (the type still standing through the anticipation), and after the next
 * card's arrival it lands, as that card lands. */
const GO = 0.8;
const LAND = 0.25;
/** Beats before the last card's leave the pull back onto the whole wall starts: twice GO, since it travels farthest. */
const PULL = 2 * GO;

/** A cubic through `keys` ([u, value, slope]), each piece a Hermite curve. */
const through = (keys: number[][], u: number) => {
  let i = 0;
  while (i < keys.length - 2 && u > keys[i + 1][0]) i++;
  const [u0, v0, m0] = keys[i];
  const [u1, v1, m1] = keys[i + 1];
  const d = u1 - u0;
  const s = clamp01((u - u0) / d);
  return (2 * s ** 3 - 3 * s ** 2 + 1) * v0 + (s ** 3 - 2 * s ** 2 + s) * d * m0 + (-2 * s ** 3 + 3 * s ** 2) * v1 + (s ** 3 - s ** 2) * d * m1;
};

/** How far along a move is at time `u` (0 to 1): back by `lean`, then fast through the middle, past by `over`, and
 * settled. */
const pathOf = (mv: Move, u: number) => {
  const mid = (1 + mv.over - mv.lean) / 2;
  const fast = (1.6 * (1 + mv.over + mv.lean)) / (B - A);
  return through([[0, 0, 0], [A, -mv.lean, 0], [(A + B) / 2, mid, fast], [B, 1 + mv.over, 0], [1, 1, 0]], u);
};

const closerFraming = (plan: Plan): Framing => ({c: [plan.W / 2, plan.H / 2], h: plan.H, z: COVER_Z, fov: CLOSER_FOV, yaw: 0, pitch: 0, roll: 0});

const mixF = (a: Framing, b: Framing, u: number): Framing => ({
  c: mixPt(a.c, b.c, u), h: a.h * Math.pow(b.h / a.h, u), z: lerp(a.z, b.z, u), fov: lerp(a.fov, b.fov, u),
  yaw: lerp(a.yaw, b.yaw, u), pitch: lerp(a.pitch, b.pitch, u), roll: lerp(a.roll, b.roll, u),
});

/** Move `mv` from `a` to `b` at time `u` (0 to 1). */
const travel = (a: Framing, b: Framing, u: number, mv: Move): Framing => {
  const m = mixF(a, b, pathOf(mv, u));
  const bell = Math.sin(Math.PI * clamp01((u - A) / (B - A)));
  const lean = Math.sin(Math.PI * clamp01(u / (2 * A)));
  const dx = b.c[0] - a.c[0];
  const dy = b.c[1] - a.c[1];
  const len = Math.max(1, Math.hypot(dx, dy));
  const scale = Math.max(a.h, b.h);
  const lx = Math.max(-1, Math.min(1, dx / scale));
  const ly = Math.max(-1, Math.min(1, dy / scale));
  const turn = lx >= 0 ? 1 : -1;
  const bow = mv.bow * len * bell * turn;
  return {...m, c: [m.c[0] - (dy / len) * bow, m.c[1] + (dx / len) * bow], h: m.h * (1 + mv.back * bell) * (1 - mv.dip * lean),
    yaw: m.yaw - mv.look * lx * (bell - 0.4 * lean), pitch: m.pitch - 0.6 * mv.look * ly * (bell - 0.4 * lean),
    roll: m.roll + mv.bank * turn * (bell - 0.3 * lean)};
};

export type Shot = {framing: Framing; travel: Partial<Travel>};

/** A framing turned by a move's nudge. */
const nudged = (f: Framing, n: Nudge): Framing => ({
  ...f, h: f.h * (n.scale ?? 1), c: [f.c[0] + (n.dx ?? 0) * f.h, f.c[1] + (n.dy ?? 0) * f.h], roll: f.roll + (n.roll ?? 0),
});

/** Whether the style's cut into beat `i` jumps. */
const jumps = (plan: Plan, i: number) => Boolean(cutOf(plan.steps[i]?.transition)?.jump);

/** When the camera holds on each card: from its landing (or, after a jump, the cut onto it) to the start of the move
 * out (or, before a jump, the cut away); and the moment of each cut, `cuts[i]` the one into beat i. */
const scheduleOf = (plan: Plan) => {
  const {cards} = plan;
  const last = cards.length - 1;
  const C = plan.closer.at;
  const goes = cards.map((c, i) => c.leave - (i === last ? PULL : GO));
  const cuts = plan.steps.map((st, i) => {
    if (i === 0) return st.at;
    if (jumps(plan, i)) return st.at;
    return i <= last ? (goes[i - 1] + cards[i].arrive + LAND) / 2 : (goes[last] + C + 1.25) / 2;
  });
  const from = cards.map((c, i) => (i === 0 ? 0 : jumps(plan, i) ? cuts[i] : c.arrive + LAND));
  const to = cards.map((c, i) => (jumps(plan, i + 1) ? cuts[i + 1] : goes[i]));
  return {from, to, cuts};
};

type Box4 = [number, number, number, number];

/** A box of card `c`'s frame, [x0, y0, x1, y1] px, where it stands in the film's frame while the camera holds on the
 * card: the hook fills the frame, and every other hold frames its card between WIDE and TIGHT about the middle. */
const heldBox = (plan: Plan, c: Card, b: Box4): Box4 => {
  const k = c.hook ? 1 : (WIDE + TIGHT) / 2;
  const x = (v: number) => plan.W / 2 + (v - plan.W / 2) / k;
  const y = (v: number) => plan.H / 2 + (v - plan.H / 2) / k;
  return [x(b[0]), y(b[1]), x(b[2]), y(b[3])];
};

/** Where a card's name and words stand in its frame, [x0, y0, x1, y1] px, from their baselines and sizes; none on a
 * card without words. */
const typeOf = (plan: Plan, c: Card): Box4 | undefined => {
  const lines = [...c.head, ...c.lines].filter((ln) => ln.text.trim());
  if (!lines.length) return undefined;
  const ys = lines.flatMap((ln) => [ln.y - ln.size, ln.y + 0.3 * ln.size]);
  const x0 = Math.min(...lines.map((ln) => ln.x));
  return [x0, Math.min(...ys), Math.max(x0 + 1, plan.W - x0), Math.max(...ys)];
};

/** The film's beats and the moments of the cuts between them. On a card's beat the move is handed where the
 * photograph and the card's type stand while the camera holds on it, and the beats it holds there, so a mark drawn on
 * the print lands on the print and is gone before the camera leaves it. */
export const timelineOf = (plan: Plan): Timeline => {
  const {from, to, cuts} = scheduleOf(plan);
  return {
    beats: plan.steps.map((s) => {
      const i = plan.cards.findIndex((c) => c.key === s.id);
      const c = plan.cards[i];
      const type = c ? typeOf(plan, c) : undefined;
      return {id: s.id, form: s.form, at: s.at, end: s.end, move: s.move, transition: s.transition, words: s.words, label: s.label, peak: s.peak,
        ...(c ? {box: heldBox(plan, c, photoBoxOf(plan, c)), ...(type ? {type: heldBox(plan, c, type)} : {}), held: [from[i], to[i]] as Pt} : {})};
    }),
    cuts,
  };
};

/** The camera's framing at beat `t`, before the beat's move turns it. */
const baseAt = (plan: Plan, t: number): Framing => {
  const cards = plan.cards;
  const C = plan.closer.at;
  const last = cards.length - 1;
  const {from, to} = scheduleOf(plan);
  const open = bezier(plan.ease.enter);
  for (let i = 0; i <= last; i++) {
    const c = cards[i];
    if (t < from[i]) continue;
    if (t <= to[i]) {
      const hold = smooth(clamp01((t - from[i]) / Math.max(0.1, to[i] - from[i])));
      const wide = c.hook ? 1 + 0.12 * (1 - span(t, 0, 0.35, open)) : 1;
      const f = holdOf(plan, i, hold);
      return {...f, h: f.h * wide};
    }
    if (i < last && t < from[i + 1]) {
      const raw = clamp01((t - to[i]) / Math.max(0.05, from[i + 1] - to[i]));
      return travel(holdOf(plan, i, 1), holdOf(plan, i + 1, 0), raw, moveInto(cards[i + 1]));
    }
  }
  // the pull back from the last card onto the whole wall, landing as the cover slams (or, when the style cuts into the
  // closer, the whole wall from the cut); then pushed for a moment by the slam and by the last figure's punch, and
  // otherwise framed exactly as the closer is posted
  const end = closerFraming(plan);
  const a0 = to[last];
  const a1 = jumps(plan, plan.steps.length - 1) ? a0 : C + 1.25;
  if (t < a1) return travel(holdOf(plan, last, 1), end, clamp01((t - a0) / (a1 - a0)), BACK);
  const kick = (at: number, k: number) => (t < at ? 0 : k * Math.sin(Math.PI * clamp01((t - at) / 0.35)) * Math.exp(-(t - at) * 3));
  return {...end, h: end.h * (1 - kick(C + 1.25, 0.02) - kick(C + 3.0, 0.03))};
};

/** The camera's framing at beat `t`, turned by the beat's move, and what the move and the cut add to the travel pass. */
export const framingAt = (plan: Plan, t: number): Shot => {
  const line = timelineOf(plan);
  const look = lookOf(plan);
  return {framing: nudged(baseAt(plan, t), nudgeAt(line, look, t)), travel: fxAt(line, look, t)};
};

/** Whether a cut that jumps falls in (a, b]. */
const jumped = (plan: Plan, a: number, b: number) =>
  scheduleOf(plan).cuts.some((c, i) => i > 0 && c > a && c <= b && jumps(plan, i));

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

/** The pose at beat `t` and the travel pass for it: the blur of the move the shutter saw over the last half frame (a
 * sideways move and a push each held under BLUR, so a move reads as travel and the picture stays; none across a jump),
 * what the beat's move and the cut add, and the film's time for the operator's hand, which stops at the stop. The
 * vignette is the card's finish alone. */
const BLUR = 0.035;
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
  const cap = (v: number) => Math.max(-BLUR, Math.min(BLUR, v));
  // a jump is a new shot, never a move the shutter saw
  const cut = jumped(plan, t - half, t);
  const smear: [number, number] = cut ? [0, 0] : [cap((b.x - a.x) * 0.5), cap((b.y - a.y) * 0.5)];
  const zoom = cut ? 0 : Math.min(BLUR, Math.abs(Math.log(was.framing.h / now.framing.h)));
  return {
    pose,
    travel: {zoom, center: [0.5, 0.5], smear: Math.hypot(...smear) < 0.0008 ? [0, 0] : smear, warp: 0, burn: 0, vignette: 0,
      time: Math.min(t, plan.closer.still) * 0.25, ...now.travel},
  };
};
