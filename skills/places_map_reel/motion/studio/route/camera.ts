// The places film's one camera: a station at every stop (the stop's card filling the picture, pushing in and turning a
// little about the card, so the map behind the band slides at its own rate), the moves between near stations in turn
// (a rise over the map that shows every near place and the route between them, and a lift, coming down onto the map as
// the photograph folds off it and riding the dot low along the leg as it runs it), each leaving with a small step
// back and landing a little past the next place before it settles, a far move that pulls back to show the whole way,
// and the closer's framing of the whole map it settles into. The film opens wide on the whole route and comes down
// onto the first place as its photograph opens out of its pin.
import * as THREE from 'three';
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, mixPt, span, type Pt} from '../../system/three/motion';
import {legDrawn} from './dot';
import type {Travel} from '../../system/three/travel';
import {along, liftOf, type Card, type Plan} from './plan';

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

export const HOLD_FOV = 30;
const CLOSER_FOV = 18;
/** Beats after the closer begins that the camera settles on the whole map. */
export const CLOSER_LAND = 0.25;

/** The framing that shows card `c`'s frame whole. */
export const stationOf = (plan: Plan, c: Card): Framing => ({c: [c.pin[0], c.pin[1]], h: plan.H * c.s, z: liftOf(c), fov: HOLD_FOV, yaw: 0, pitch: 0, roll: 0});

/** The share of the card's frame the camera holds as it lands and as it leaves (board_drive.py HOLD_END lays the card's
 * type inside the type-safe area at the second), and how far it turns about the card over the hold, radians: the card
 * stays framed while the map behind it, farther from the lens, slides past. */
const HOLD_PUSH: [number, number] = [0.985, 0.955];
/** The film opens on the whole route, every place and the way between them inside the frame with ROUTE_ROOM of it to
 * spare, and the camera comes down onto the first place over the hook's settle, starting from rest. */
const ROUTE_ROOM = 1.45;
const HOLD_TURN = 0.1;

/** The framing that holds the whole route: every pin and every leg's way inside the frame. */
export const routeFraming = (plan: Plan): Framing => {
  const pts = [...plan.cards.map((c) => c.pin), ...plan.legs.flatMap((l) => l.pts)];
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const h = Math.max(y1 - y0, ((x1 - x0) * plan.H) / plan.W) * ROUTE_ROOM;
  return {c: [(x0 + x1) / 2, (y0 + y1) / 2], h: Math.max(h, 0.35 * plan.H), z: 0, fov: HOLD_FOV, yaw: 0, pitch: 0, roll: 0};
};

/** The camera on card `c` at `u` of its hold, 0 as it lands to 1 as it leaves. */
export const holdFraming = (plan: Plan, c: Card, u: number): Framing => {
  const st = stationOf(plan, c);
  const way = c.west ? -1 : 1;
  return {...st, h: st.h * lerp(HOLD_PUSH[0], HOLD_PUSH[1], u), yaw: way * HOLD_TURN * (u - 0.5), pitch: 0.4 * HOLD_TURN * (u - 0.5)};
};

/** A move's progress for the place the camera frames: a small step back as it leaves, and a little past the next place
 * as it lands, settling back onto it. */
const ANTICIPATE = bezier([0.5, -0.2, 0.3, 1.14]);

export const closerFraming = (plan: Plan): Framing => ({c: [plan.W / 2, plan.H / 2], h: plan.H, z: 0, fov: CLOSER_FOV, yaw: 0, pitch: 0, roll: 0});

/** The way from one framing's center to the next: along the leg for a stop, straight to the closer. */
const pathOf = (plan: Plan, i: number) => {
  const leg = plan.legs[i];
  if (leg) return (u: number) => along(leg, u);
  const a = plan.cards[i].pin;
  const b: Pt = [plan.W / 2, plan.H / 2];
  return (u: number) => mixPt(a, b, u);
};

/** The window of the move out of card `i`: from the camera leaving it to the camera landing on what follows. */
export const moveOf = (plan: Plan, i: number): [number, number] => {
  const c = plan.cards[i];
  return [c.goAt, i + 1 < plan.cards.length ? c.landAt : plan.closer.at + CLOSER_LAND];
};

/** How much of the map a lift holds, as a share of the taller of the two stations: low over the map, the dot at the
 * middle of the picture. */
const LIFT_ROOM = 1.3;

/** A move from `a` to `b` at progress `u` (already eased): a rise climbs over the near places, a lift comes down onto
 * the leg, easing in from the station it leaves and out onto the one it reaches; far legs and the move into the closer
 * follow `path` and pull back to show the whole way. Each leans back behind its way. */
const travel = (plan: Plan, i: number, a: Framing, b: Framing, u: number, uc: number, t: number, path: (u: number) => Pt, chord: number, closer: boolean): Framing => {
  const bell = Math.sin(Math.PI * u);
  const kind = plan.cards[i].travel;
  const near = !closer && !plan.legs[i].far;
  const ux = (b.c[0] - a.c[0]) / Math.max(1, chord);
  const uy = (b.c[1] - a.c[1]) / Math.max(1, chord);
  const tilt = (closer ? 0.18 : near ? 0.25 : 0.42) * bell;
  const pitch = Math.asin(-Math.sin(tilt) * uy);
  const yaw = Math.asin(Math.max(-1, Math.min(1, (-Math.sin(tilt) * ux) / Math.cos(pitch))));
  const from = {yaw: lerp(a.yaw, b.yaw, u), pitch: lerp(a.pitch, b.pitch, u)};
  const turn = {z: lerp(a.z, b.z, u), fov: lerp(a.fov, b.fov, u) + 6 * bell, yaw: from.yaw + yaw, pitch: from.pitch + pitch, roll: 0.05 * ux * bell};
  if (near && kind === 'rise') {
    // up over the map until every near place stands in the frame, the way the dot has come drawn between them,
    // the camera tipped back so the map lies ahead of it, then down onto the next place
    const pins = plan.cards.filter((c) => !c.far).map((c) => c.pin);
    const tall = Math.max(...pins.map((q) => q[1])) - Math.min(...pins.map((q) => q[1]));
    const across = Math.max(...pins.map((q) => q[0])) - Math.min(...pins.map((q) => q[0]));
    const wide = Math.max(2.3 * Math.max(a.h, b.h), 1.3 * Math.max(tall, (across * plan.H) / plan.W));
    const h = a.h * Math.pow(b.h / a.h, u) * Math.pow(wide / Math.sqrt(a.h * b.h), Math.pow(bell, 0.7));
    return {c: mixPt(a.c, b.c, uc), h, ...turn, pitch: from.pitch + 0.32 * bell, yaw: from.yaw + 0.5 * yaw, roll: 0};
  }
  if (near) {
    // a lift: down from the photograph's height onto the map as the photograph folds off it, riding the dot low along
    // the leg as it runs it, rolling a little into the way it goes, and up onto the next photograph opening out of its pin
    const dot = along(plan.legs[i], legDrawn(plan, i, t));
    const w = Math.sqrt(bell);
    const h = a.h * Math.pow(b.h / a.h, u) * Math.pow(LIFT_ROOM, w);
    return {c: mixPt(mixPt(a.c, b.c, uc), dot, w), h, ...turn, z: turn.z * (1 - w), roll: 0.1 * Math.sign(ux || 1) * bell};
  }
  if (closer) {
    const h = a.h * Math.pow(b.h / a.h, u) * Math.pow(1.15, bell);
    return {c: path(u), h, ...turn};
  }
  // a far move pulls back early and holds wide, reaching at its middle the height that holds the whole way across the
  // frame, so the dot never crosses an empty sea
  const h = a.h * Math.pow(b.h / a.h, u) * Math.pow(farView(plan, a, b) / Math.sqrt(a.h * b.h), Math.pow(bell, 0.35));
  return {c: path(u), h, ...turn};
};

/** The height of the picture at the middle of a far move from `a` to `b`: the whole way from one place to the other
 * inside the frame, across its width as well as its height. */
const farView = (plan: Plan, a: Framing, b: Framing) =>
  Math.max(1.7 * Math.max(a.h, b.h), 1.15 * Math.max(Math.abs(b.c[1] - a.c[1]), (Math.abs(b.c[0] - a.c[0]) * plan.H) / plan.W));

/** How much closer the camera presses, about the middle of the route, while the title holds over it: the whole route
 * stays in the frame until the dive. */
const HOOK_PRESS = 0.05;

export type Shot = {framing: Framing; travel: Partial<Travel>};

/** The camera's framing at beat `t`, with the extra travel treatment its move carries. */
export const framingAt = (plan: Plan, t: number): Shot => {
  const move = bezier(plan.ease.move);
  const cards = plan.cards;
  for (let i = 0; i < cards.length; i++) {
    const c = cards[i];
    const from = i === 0 ? 0 : moveOf(plan, i - 1)[1];
    const [go, land] = moveOf(plan, i);
    if (t < from) continue;
    if (t <= go) {
      const hold = holdFraming(plan, c, clamp01((t - from) / Math.max(0.1, go - from)));
      if (i > 0 || t >= plan.hook.settle) return {framing: hold, travel: {}};
      // the whole route held wide under the title, pressing in a little, then the dive onto the first place
      const wide = routeFraming(plan);
      const {dive, settle} = plan.hook;
      const pressed = {...wide, h: wide.h * (1 - HOOK_PRESS * span(t, 0, dive, bezier([0.3, 0, 0.7, 1])))};
      if (t < dive) return {framing: {...pressed, yaw: hold.yaw, pitch: hold.pitch}, travel: {}};
      const u = span(t, dive, settle - dive, bezier([0.5, 0, 0.15, 1]));
      return {framing: {...hold, c: mixPt(pressed.c, hold.c, u), h: pressed.h * Math.pow(hold.h / pressed.h, u), z: lerp(pressed.z, hold.z, u)}, travel: {}};
    }
    if (t < land) {
      const raw = clamp01((t - go) / (land - go));
      const u = move(raw);
      const a = holdFraming(plan, c, 1);
      const next = cards[i + 1];
      const b = next ? holdFraming(plan, next, 0) : closerFraming(plan);
      const chord = Math.hypot(b.c[0] - a.c[0], b.c[1] - a.c[1]);
      const tr: Partial<Travel> = {};
      if (i === 0) tr.warp = 0.035 * Math.sin(Math.PI * u);
      return {framing: travel(plan, i, a, b, u, ANTICIPATE(raw), t, pathOf(plan, i), chord, !next), travel: tr};
    }
  }
  const end = closerFraming(plan);
  const C = plan.closer.at + CLOSER_LAND;
  const settle = span(t, C, Math.max(0.5, plan.closer.still - C), bezier([0.2, 0.6, 0.3, 1]));
  return {framing: {...end, h: end.h * (1 + 0.09 * (1 - settle))}, travel: {}};
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

/** The pose at beat `t`, the travel pass for it (the blur of the move the shutter saw over the last half frame and
 * the chosen treatment; the vignette is the card's finish), how far the camera stands from what it frames, and the wall px the picture is tall.
 * The shutter opens no earlier than the film's first frame, so the first frame is sharp. */
export const shotAt = (plan: Plan, t: number): {pose: Pose; travel: Travel; distance: number; h: number} => {
  const now = framingAt(plan, t);
  const half = 0.5 / plan.pulse;
  const was = framingAt(plan, Math.max(0, t - half));
  const pose = poseOf(plan, now.framing);
  const prev = poseOf(plan, was.framing);
  const aspect = plan.W / plan.H;
  const p = new THREE.Vector3(...pose.target);
  setCam(prev, aspect);
  const a = p.clone().project(cam);
  setCam(pose, aspect);
  const b = p.clone().project(cam);
  const cap = (v: number, m: number) => Math.max(-m, Math.min(m, v));
  // light, so a fast move keeps the photographs' own values and never smears them into the paper
  const smear: [number, number] = [cap((b.x - a.x) * 0.2, 0.02), cap((b.y - a.y) * 0.2, 0.02)];
  const zoom = Math.min(0.03, Math.abs(Math.log(was.framing.h / now.framing.h)) * 0.6);
  const distance = now.framing.h / 2 / Math.tan((now.framing.fov * Math.PI) / 360);
  return {
    pose,
    travel: {zoom, center: [0.5, 0.5], smear: Math.hypot(...smear) < 0.0008 ? [0, 0] : smear, warp: 0, burn: 0, vignette: 0, time: t * 0.25, ...now.travel},
    distance,
    h: now.framing.h,
  };
};
