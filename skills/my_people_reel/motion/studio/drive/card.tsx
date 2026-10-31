// A photograph's card on the wall: the picture flies in as a tile and the blade crosses its edge. On the hook the part
// above the edge peels toward the camera, uncovering the field. On a person's card the photograph keeps the whole
// frame: the part above the edge lifts off the part under it as a second layer, sharp, throwing its shadow down
// across the cut with its lit rim along the blade, and the type stands in front of it. When the camera leaves,
// the part above the edge hinges away and the picture trims down into its slice of the closer's wall, where it stays.
//
// The card arrives the way the beat's move draws it (dropped, slapped, popped, slid, slammed, stretched, risen, or
// simply there on the cut). A framed photograph is a print mounted the way the style mounts one: taped to the page,
// projected on the dark with its light spilling round it, or flat on the ink; the mount drifts behind the print slower
// than the print as the camera holds (FIELD). On a photograph that fills the frame the part lifted above the edge moves
// more than the part under it, as the nearer layer (NEAR). Every card that floats over the wall throws its shadow on
// the slices already resting there.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span, type Pt} from '../../system/three/motion';
import type {Framing} from './camera';
import {onWall, type Card, type Plan} from './plan';

export const cardScale = (c: Card) => c.T.s;
/** How far a card stands off the wall while it is the one the camera is on. */
export const liftOf = (c: Card) => 90 * c.T.s;
/** The depth a card's type stands at while the camera is on it: in front of the layer the photograph lifts. */
export const typeZ = (c: Card) => liftOf(c) + (c.field === 'photo' ? 100 : 7) * c.T.s;
/** Where a card rests once it is in its slice: a hair over the cards before it. */
export const restZ = (index: number) => 0.03 * (index + 1);
const MARGIN = 0.12;
/** How far the operator's hand can carry the held picture off its framing, as a fraction of its height. */
const HAND = 0.02;
/** How much less than the print a framed photograph's field moves as the camera holds, and how much more than the
 * part under the edge the lifted part above it moves on a photograph that fills the frame. */
const FIELD = 0.45;
const NEAR = 0.15;
/** The print's shadow on its field: how far it spreads past the print and how far down the light throws it, px; the
 * light along its cut edges, px across. */
const SPREAD = 64;
const DROP = 26;
const WRAP = 24;
/** Beats after a card's arrival that its keepsake starts to land, and how long it takes to. */
const KEEP_AT = 0.6;
const KEEP_IN = 0.35;

/** The edge's y in the piece frame at x. */
const edgeY = (c: Card, W: number, x: number) => c.line[0] + ((c.line[1] - c.line[0]) * x) / W;

/** The card's three quads in piece-frame px: the picture below the edge, the picture above it, the field above it. */
export const quadsOf = (c: Card, W: number, H: number) => {
  const [px, py, pw, ph] = c.place;
  const x0 = Math.max(-MARGIN * W, px), x1 = Math.min((1 + MARGIN) * W, px + pw);
  const yb = Math.min((1 + MARGIN) * H, py + ph), ya = Math.max(-MARGIN * H, py);
  const fx0 = -MARGIN * W, fx1 = (1 + MARGIN) * W;
  return {
    below: [[x0, edgeY(c, W, x0)], [x1, edgeY(c, W, x1)], [x1, yb], [x0, yb]] as Pt[],
    above: [[x0, ya], [x1, ya], [x1, edgeY(c, W, x1)], [x0, edgeY(c, W, x0)]] as Pt[],
    field: [[fx0, -MARGIN * H], [fx1, -MARGIN * H], [fx1, edgeY(c, W, fx1)], [fx0, edgeY(c, W, fx0)]] as Pt[],
  };
};

/** The card's timings in beats: its entry, the blade's peel, and the trim into its slice, which is done by the frame
 * of the cut, so the next beat's first frame never shows this card still standing over it. */
export const timesOf = (c: Card) => ({
  fly: c.hook ? [0, 0.3] : [c.arrive, 0.5],
  peel: [c.cut + 0.05, 0.5],
  leave: [c.leave - 0.01, 0.01],
});

const backOut = (u: number) => 1 + 2.70158 * Math.pow(u - 1, 3) + 1.70158 * Math.pow(u - 1, 2);

/** How a card stands off its landing at `u` of its entry (0 as it starts, 1 landed), and how much of the lens distance
 * it starts from. The hook falls flat from the lens; every other card arrives the way its beat's move draws it:
 * `drop` falls from above, turned, and lands with a bounce; `slap` lands oversize and snaps flat; `pop` grows from
 * small past its size and settles; `slide` comes in along its edge; `slam` drops from by the lens and hits; `stretch`
 * opens from a sliver along its edge; `zoom` closes in from wide onto its framing; `rise` comes up square to its edge,
 * tipping flat; `cut` is simply there. A card
 * that travels in starts with most of its picture already in the frame, so the cut never lands on an empty one. */
const entryOf = (c: Card, axis: THREE.Vector3, u: number, w: number, h: number) => {
  const m = new THREE.Matrix4();
  const up = new THREE.Vector3(-axis.y, axis.x, 0);
  const tilt = (about: THREE.Vector3, angle: number) => new THREE.Matrix4().makeRotationAxis(about, angle);
  const scaled = (k: number) => new THREE.Matrix4().makeScale(k, k, 1);
  if (c.hook) {
    const rest = 1 - bezier([0.12, 0.8, 0.25, 1])(u);
    return {turn: m.makeRotationFromEuler(new THREE.Euler(rest * -0.5, rest * -0.45, rest * 0.12)), near: 0.82 * rest};
  }
  switch (c.entry) {
    case 'drop': {
      const rest = 1 - backOut(u);
      const from = up.clone().multiplyScalar(0.5 * h * rest);
      return {turn: m.makeTranslation(from.x, from.y, 0).multiply(new THREE.Matrix4().makeRotationZ(rest * 0.22)), near: 0.25 * Math.max(0, rest)};
    }
    case 'slap': {
      const rest = 1 - bezier([0.2, 0.95, 0.3, 1])(u);
      return {turn: scaled(1 + 0.15 * rest), near: 0};
    }
    case 'pop':
      return {turn: scaled(0.6 + 0.4 * backOut(u)), near: 0};
    case 'slide': {
      const rest = 1 - bezier([0.12, 0.8, 0.25, 1])(u);
      const from = axis.clone().multiplyScalar(-0.45 * w * rest);
      return {turn: m.makeTranslation(from.x, from.y, 0).multiply(tilt(up, rest * 0.2)), near: 0};
    }
    case 'slam': {
      const rest = 1 - bezier([0.7, 0, 0.84, 0])(u);
      return {turn: m.makeRotationZ(rest * 0.06), near: 0.85 * rest};
    }
    case 'stretch': {
      const k = 0.3 + 0.7 * bezier([0.2, 0.9, 0.3, 1])(u);
      const a = Math.atan2(axis.y, axis.x);
      return {turn: new THREE.Matrix4().makeRotationZ(a).multiply(new THREE.Matrix4().makeScale(k, 1, 1)).multiply(new THREE.Matrix4().makeRotationZ(-a)), near: 0};
    }
    case 'zoom':
      return {turn: scaled(1 + 0.3 * (1 - bezier([0.25, 0.8, 0.3, 1])(u))), near: 0};
    case 'cut':
      return {turn: m, near: 0};
    default: {
      const rest = 1 - bezier([0.12, 0.8, 0.25, 1])(u);
      const from = up.clone().multiplyScalar(-0.16 * h * rest);
      return {turn: m.makeTranslation(from.x, from.y, 0).multiply(tilt(axis, rest * -0.6)), near: 0.12 * rest};
    }
  }
};

type Quad = {mesh: THREE.Mesh; geo: THREE.BufferGeometry};

const quad = (mat: THREE.Material): Quad => {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(12), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(8), 2));
  geo.setIndex([0, 3, 1, 1, 3, 2]);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  return {mesh, geo};
};

/** Sets a quad's corners (world) and their texture coordinates. */
const setQuad = (q: Quad, pts: THREE.Vector3[], uvs: Pt[]) => {
  const pos = q.geo.getAttribute('position') as THREE.BufferAttribute;
  const uv = q.geo.getAttribute('uv') as THREE.BufferAttribute;
  pts.forEach((p, i) => pos.setXYZ(i, p.x, p.y, p.z));
  uvs.forEach((u, i) => uv.setXY(i, u[0], u[1]));
  pos.needsUpdate = true;
  uv.needsUpdate = true;
  q.geo.computeBoundingSphere();
};

let gradient: THREE.Texture | null = null;
/** A ramp from opaque at its top edge to clear at its bottom, for the shadow the field's edge throws on the picture. */
const ramp = () => {
  if (gradient) return gradient;
  const cv = document.createElement('canvas');
  cv.width = 4;
  cv.height = 128;
  const g = cv.getContext('2d')!;
  const lg = g.createLinearGradient(0, 0, 0, 128);
  lg.addColorStop(0, 'rgba(0,0,0,1)');
  lg.addColorStop(0.25, 'rgba(0,0,0,0.45)');
  lg.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = lg;
  g.fillRect(0, 0, 4, 128);
  gradient = new THREE.CanvasTexture(cv);
  return gradient;
};

let fading: THREE.Texture | null = null;
/** A ramp from clear at its top edge to opaque at its bottom, eased in, for the dark that rises behind a card's type. */
const fade = () => {
  if (fading) return fading;
  const cv = document.createElement('canvas');
  cv.width = 4;
  cv.height = 128;
  const g = cv.getContext('2d')!;
  const lg = g.createLinearGradient(0, 0, 0, 128);
  for (let i = 0; i <= 8; i++) lg.addColorStop(i / 8, `rgba(0,0,0,${(Math.pow(i / 8, 1.6)).toFixed(3)})`);
  g.fillStyle = lg;
  g.fillRect(0, 0, 4, 128);
  fading = new THREE.CanvasTexture(cv);
  return fading;
};

/** The soft shadow a print taped to the page throws on it: a dark box over its paper, `inset` of the texture's width and
 * height in from each side and `down` of its height lower, blurred out to the texture's edges. */
const soft = (w: number, h: number, inset: [number, number], down: number) => {
  const cv = document.createElement('canvas');
  cv.width = 256;
  cv.height = Math.max(16, Math.round((256 * h) / w));
  const g = cv.getContext('2d')!;
  const [ix, iy] = [inset[0] * cv.width, inset[1] * cv.height];
  g.shadowColor = 'rgba(0,0,0,1)';
  g.shadowBlur = Math.min(ix, iy) * 0.9;
  g.shadowOffsetX = 4 * cv.width;
  g.fillStyle = '#000000';
  g.fillRect(ix - 4 * cv.width, iy + down * cv.height, cv.width - 2 * ix, cv.height - 2 * iy);
  return new THREE.CanvasTexture(cv);
};

/** `pts` turned `angle` radians about their middle. */
const turnedAbout = (pts: Pt[], mid: Pt, angle: number) => {
  const [c, s] = [Math.cos(angle), Math.sin(angle)];
  return pts.map(([x, y]) => [mid[0] + (x - mid[0]) * c - (y - mid[1]) * s, mid[1] + (x - mid[0]) * s + (y - mid[1]) * c] as Pt);
};

/** `pts`' y held inside [y0, y1]. */
const within = (pts: Pt[], y0: number, y1: number) => pts.map(([x, y]) => [x, Math.min(y1, Math.max(y0, y))] as Pt);

/** The camera on a card: where it holds now (`held`) and its station. A layer `far` of the way to standing still moves
 * and grows that much less than the print as the camera moves in from the station, so it reads as further behind (a
 * negative `far` moves more, nearer). A layer behind that has to fill the picture (`fills`: its left, right and foot
 * on the wall, and the picture's width over its height) grows about the held middle just as much as it takes to keep
 * filling the picture the camera holds and the operator's hand around it (HAND of the picture's height on every side),
 * so the wall never shows at the picture's sides or foot. */
export type View = {held: Framing; station: Framing};
const drifted = (v: View, far: number, fills?: {x: Pt; foot: number; aspect: number}) => {
  if (far === 0) return (p: Pt) => p;
  const {held: h, station: s} = v;
  const cx = s.c[0] + (h.c[0] - s.c[0]) * (1 - far), cy = s.c[1] + (h.c[1] - s.c[1]) * (1 - far);
  let k = Math.pow(h.h / s.h, far);
  if (fills) {
    const pad = HAND * h.h;
    const need = [[(h.h * fills.aspect) / 2 + pad, cx - fills.x[0]], [(h.h * fills.aspect) / 2 + pad, fills.x[1] - cx], [h.h / 2 + pad, fills.foot - cy]];
    for (const [half, room] of need) if (room > 1) k = Math.max(k, half / room);
  }
  return (p: Pt): Pt => [h.c[0] + (p[0] - cx) * k, h.c[1] + (p[1] - cy) * k];
};

export type CardProps = {plan: Plan; card: Card; index: number; t: number; texture: THREE.Texture; keepTexture?: THREE.Texture; view: View};

/** What a framed print is mounted on, from the card's photo beat: the color under it (the card's ground), the color of
 * the light along its edges (none: no light and no shadow), how far that light spreads, and the colors of the tape
 * across its top corners (none: no tape). The mount's kind says how the print sits: `projected` throws its light round
 * it on the dark, `flat` lies on the ground with no edge, and a taped print is a print in its white border, turned the
 * card's tilt (each other print the other way), casting a soft shadow on the page. */
const mountOf = (plan: Plan, mount: string | null) => {
  const k = plan.colors;
  const role = (x: string) => k[x] ?? x;
  const pic = plan.photo.picture;
  const ground = role(plan.photo.ground);
  const tape = pic.tape > 0 ? Array.from({length: Math.min(2, pic.tape)}, () => role(pic.tapeColor)) : null;
  if (mount === 'projected') return {ground, rim: k.accent, wrap: 3, rimOn: 0.75, shadow: 0.9, tape, border: 0, tilt: 0};
  if (mount === 'flat') return {ground, rim: null, wrap: 1, rimOn: 0, shadow: 0, tape, border: 0, tilt: 0};
  return {ground, rim: role(pic.rimColor), wrap: 1, rimOn: 0, shadow: 0.55, tape, border: pic.rim, tilt: pic.tilt};
};

export const CardView: React.FC<CardProps> = ({plan, card: c, index, t, texture, keepTexture, view}) => {
  const {W, H} = plan;
  const mount = mountOf(plan, c.mount);
  const parts = useMemo(() => {
    // a framed photograph's own layers draw its mount; the print over them draws the photograph
    const mounted = (extra: THREE.MeshBasicMaterialParameters) =>
      new THREE.MeshBasicMaterial(c.band ? {color: mount.ground, toneMapped: false, side: THREE.DoubleSide, ...extra} : {map: texture, toneMapped: false, side: THREE.DoubleSide, ...extra});
    const photo = mounted({});
    const above = mounted({transparent: true});
    // the shadow and light over the picture under the edge stand a hair in front of it: far from the lens that hair is
    // under the depth buffer's step, so each is also drawn that many steps nearer than its depth (the further over, the
    // more); none writes depth, so the type and tags over the wall are never hidden by them
    const nearer = (k: number) => ({polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -2 * k});
    const print = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, side: THREE.DoubleSide});
    const printAbove = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, transparent: true, side: THREE.DoubleSide});
    const field = new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, side: THREE.DoubleSide});
    const shade = new THREE.MeshBasicMaterial({map: ramp(), color: '#000000', toneMapped: false, transparent: true, depthWrite: false});
    const drop = new THREE.MeshBasicMaterial({map: ramp(), color: '#000000', toneMapped: false, transparent: true, depthWrite: false, ...nearer(1)});
    const rim = new THREE.MeshBasicMaterial({map: ramp(), color: new THREE.Color(mount.rim ?? '#000000'), toneMapped: false, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, ...nearer(3)});
    const tape = (hex: string) => new THREE.MeshBasicMaterial({color: hex, toneMapped: false, transparent: true, opacity: 0.88, depthWrite: false, side: THREE.DoubleSide, ...nearer(5)});
    const tapes = (mount.tape ?? []).map((hex) => quad(tape(hex)));
    const gleam = new THREE.MeshBasicMaterial({color: new THREE.Color(1, 0.86, 0.62).multiplyScalar(4), toneMapped: false, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending});
    const scrim = new THREE.MeshBasicMaterial({map: fade(), color: '#000000', toneMapped: false, transparent: true, depthWrite: false, side: THREE.DoubleSide, ...nearer(2)});
    const dark = new THREE.MeshBasicMaterial({color: '#000000', toneMapped: false, transparent: true, depthWrite: false, side: THREE.DoubleSide, ...nearer(2)});
    const caught = new THREE.ShadowMaterial({opacity: 0.4, depthWrite: false, ...nearer(4)});
    // the border sits a hair behind the print, which far from the lens is under the depth buffer's step: it writes no
    // depth, so the print drawn after it always covers it
    const border = new THREE.MeshBasicMaterial({color: mount.rim ?? '#ffffff', toneMapped: false, depthWrite: false, side: THREE.DoubleSide});
    const [pw, ph] = [c.place[2], c.place[3] * ((c.band?.[1] ?? 1) - (c.band?.[0] ?? 0))];
    const out = SPREAD + mount.border * pw;
    const lay = new THREE.MeshBasicMaterial({map: soft(pw + 2 * out, ph + 2 * out, [out / (pw + 2 * out), out / (ph + 2 * out)], (DROP * 0.5) / (ph + 2 * out)),
      color: '#000000', toneMapped: false, transparent: true, depthWrite: false, ...nearer(1)});
    // the keepsake: its picture, its white border, its shadow on the page and its strip of tape
    const k = c.keepsake;
    const [kw, kh] = k ? [k.box[2] - k.box[0], k.box[3] - k.box[1]] : [1, 1];
    const kOut = SPREAD * 0.6 + mount.border * kw;
    const keep = k && keepTexture ? {
      photo: quad(new THREE.MeshBasicMaterial({map: keepTexture, toneMapped: false, side: THREE.DoubleSide})),
      border: quad(new THREE.MeshBasicMaterial({color: mount.rim ?? '#ffffff', toneMapped: false, depthWrite: false, side: THREE.DoubleSide})),
      lay: quad(new THREE.MeshBasicMaterial({map: soft(kw + 2 * kOut, kh + 2 * kOut, [kOut / (kw + 2 * kOut), kOut / (kh + 2 * kOut)], (DROP * 0.5) / (kh + 2 * kOut)),
        color: '#000000', toneMapped: false, transparent: true, depthWrite: false, ...nearer(1)})),
      tape: quad(tape(mount.tape?.[0] ?? '#d8d0bc')),
    } : null;
    return {
      keep, kOut,
      below: quad(photo), above: quad(above), print: quad(print), printAbove: quad(printAbove), field: quad(field), shade: quad(shade),
      dropTop: quad(drop), dropFoot: quad(drop), rimTop: quad(rim), rimFoot: quad(rim), gleam: quad(gleam), catch: quad(caught), tapes,
      border: quad(border), lay: quad(lay), scrim: quad(scrim), dark: quad(dark),
      mats: {photo, above, print, printAbove, field, shade, drop, rim, gleam, caught, lay, scrim, dark},
    };
  }, [texture, keepTexture, c.keepsake?.box.join(), c.band, c.place.join(), mount.ground, mount.rim, mount.border, mount.tape?.join()]);
  const tm = timesOf(c);
  const fly = clamp01((t - tm.fly[0]) / tm.fly[1]);
  if (t < tm.fly[0] - 0.01) return null;
  const s = c.T.s;
  const lift = liftOf(c);
  const settled = restZ(index);
  const leave = span(t, tm.leave[0], tm.leave[1]);
  const peel = span(t, tm.peel[0], tm.peel[1], bezier([0.4, 0, 0.6, 1]));
  const q = quadsOf(c, W, H);
  const w = (p: Pt) => onWall(c.T, p);
  const toWorld = (p: Pt, z: number) => new THREE.Vector3(p[0] - W / 2, H / 2 - p[1], z);
  const [px, py, pw, ph] = c.place;
  const uvOf = (p: Pt): Pt => [(p[0] - px) / pw, 1 - (p[1] - py) / ph];
  // the line the edge runs along, in world space: the axis the card flies in on and the hinges turn about
  const e0 = toWorld(w([0, c.line[0]]), 0);
  const e1 = toWorld(w([W, c.line[1]]), 0);
  const axis = e1.clone().sub(e0).normalize();
  // the card's flight: from toward the lens down onto its lift, taking its own line as it comes
  const D = (H * s) / 2 / Math.tan((30 * Math.PI) / 360);
  const {turn, near} = entryOf(c, axis, fly, W * s, H * s);
  const zFly = D * near;
  // a card whose edge stands over the frame (its photograph or page takes the whole frame) turns about its middle
  const whole = c.line[0] < 0 && c.line[1] < 0;
  const pivot = c.hook || whole ? toWorld(w([W / 2, H / 2]), 0) : e0.clone().lerp(e1, 0.5);
  const flown = (v: THREE.Vector3) => v.sub(pivot).applyMatrix4(turn).add(pivot).add(new THREE.Vector3(0, 0, zFly));
  const z = lerp(lift, settled, leave);
  // the picture under the edge, trimmed toward its slice as the camera leaves
  const belowWall = q.below.map(w);
  const belowPts = belowWall.map((p, i) => {
    const target = c.slot[i];
    return [lerp(p[0], target[0], leave), lerp(p[1], target[1], leave)] as Pt;
  });
  // texture coordinates come from the wall position through the slice's place, the same picture plane
  const wallPlace = [onWall(c.T, [px, py]), onWall(c.T, [px + pw, py + ph])];
  const uvWall = (p: Pt): Pt => [(p[0] - wallPlace[0][0]) / (wallPlace[1][0] - wallPlace[0][0]), 1 - (p[1] - wallPlace[0][1]) / (wallPlace[1][1] - wallPlace[0][1])];
  const framed = !!c.band;
  const photoCard = c.field === 'photo';
  // the layers drift apart as the camera holds and come back together as the card trims into its slice
  const rest = 1 - leave;
  const fills = {x: [wallPlace[0][0], wallPlace[1][0]] as Pt, foot: wallPlace[1][1], aspect: W / H};
  const under = drifted(view, (framed ? FIELD : 0) * rest, framed ? fills : undefined);
  const beyond = framed ? under : drifted(view, (photoCard ? -NEAR : 0) * rest);
  // a framed photograph's mount drifts down behind the print as the camera holds; its top stays tucked under the page
  // above the edge, so no gap opens along the edge onto the wall behind
  const tucked = (p: Pt, i: number): Pt => {
    const d = under(p);
    return framed && i < 2 ? [d[0], Math.min(d[1], p[1])] : d;
  };
  setQuad(parts.below, belowPts.map((p, i) => flown(toWorld(tucked(p, i), z))), belowPts.map(uvWall));
  const hinge = (pts: Pt[], zz: number, angle: number, rise: number, at: (p: Pt) => Pt = (p) => p) => {
    const m = new THREE.Matrix4().makeRotationAxis(axis, angle);
    const o = e0.clone().setZ(zz);
    return pts.map((p) => flown(toWorld(at(w(p)), zz).sub(o).applyMatrix4(m).add(o).add(new THREE.Vector3(0, rise, rise * 0.6))));
  };
  // the print: the band of the picture the photograph spans, over its field, its shadow on the field and light along
  // the edges the blade did not make
  const [b0, b1] = c.band ?? [0, 1];
  const bandTop = py + b0 * ph, bandFoot = py + b1 * ph;
  const [wTop, wFoot] = [onWall(c.T, [0, bandTop])[1], onWall(c.T, [0, bandFoot])[1]];
  // a print standing on the page is cropped at its sides until it trims into its slice
  const cropped = c.crop && leave < 0.5 ? [onWall(c.T, [c.crop[0], 0])[0], onWall(c.T, [c.crop[1], 0])[0]] : null;
  const printPts = within(belowPts, wTop, wFoot).map(([x, y]) => [cropped ? Math.min(cropped[1], Math.max(cropped[0], x)) : x, y] as Pt);
  const shown = framed && printPts[3][1] - printPts[0][1] > 1;
  // the band's own top edge, where the blade's cut is not
  const bandEdge = shown && printPts[0][1] <= wTop + 0.5 && printPts[1][1] <= wTop + 0.5;
  const bordered = shown && bandEdge && mount.border > 0;
  if (shown) {
    // a taped print stands turned on the page as the card holds and lies square once it is in its slice
    const mid: Pt = [(printPts[0][0] + printPts[2][0]) / 2, (printPts[0][1] + printPts[2][1]) / 2];
    const angle = bordered ? ((index % 2 ? -1 : 1) * mount.tilt * Math.PI * rest) / 180 : 0;
    const at = (pts: Pt[], dz: number) => turnedAbout(pts, mid, angle).map((p) => flown(toWorld(p, z + dz * s)));
    const [tl, tr, br, bl] = printPts;
    setQuad(parts.print, at(printPts, 0.4), printPts.map(uvWall));
    if (bordered) {
      // the print's white border, and its shadow laid softly on the page all round it, thrown a little down
      const b = mount.border * (tr[0] - tl[0]);
      const grow = (d: number): Pt[] => [[tl[0] - d, tl[1] - d], [tr[0] + d, tr[1] - d], [br[0] + d, br[1] + d], [bl[0] - d, bl[1] + d]];
      setQuad(parts.border, at(grow(b), 0.3), [[0, 1], [1, 1], [1, 0], [0, 0]]);
      setQuad(parts.lay, at(grow(b + SPREAD * s), 0.2), [[0, 1], [1, 1], [1, 0], [0, 0]]);
      parts.mats.lay.opacity = mount.shadow * rest;
    }
    // the shadow, thrown down: a short reach above the print, a longer one under it
    const drop = DROP * s, spread = SPREAD * s, wrap = WRAP * s * mount.wrap;
    const up = (p: Pt, d: number): Pt => [p[0], p[1] - d];
    setQuad(parts.dropTop, at([up(tl, spread - drop), up(tr, spread - drop), up(tr, -drop), up(tl, -drop)], 0.2), [[0, 0], [1, 0], [1, 1], [0, 1]]);
    setQuad(parts.dropFoot, at([bl, br, up(br, -drop - spread), up(bl, -drop - spread)], 0.2), [[0, 1], [1, 1], [1, 0], [0, 0]]);
    setQuad(parts.rimTop, at([tl, tr, up(tr, -wrap), up(tl, -wrap)], 0.6), [[0, 1], [1, 1], [1, 0], [0, 0]]);
    setQuad(parts.rimFoot, at([up(bl, wrap), up(br, wrap), br, bl], 0.6), [[0, 0], [1, 0], [1, 1], [0, 1]]);
    parts.mats.drop.opacity = mount.shadow * rest;
    parts.mats.rim.opacity = mount.rimOn * rest;
    // two strips of tape across the print's top corners, each turned its own way, slapped on as the card lands
    parts.tapes.forEach((q, k) => {
      const out = bordered ? mount.border * (tr[0] - tl[0]) : 0;
      const corner: Pt = k === 0 ? [tl[0] - out, tl[1] - out] : [tr[0] + out, tr[1] - out];
      const len = 0.2 * W * s, thick = 0.035 * H * s;
      const a = ((k === 0 ? -1 : 1) * 38 * Math.PI) / 180;
      const [ux, uy] = [Math.cos(a), Math.sin(a)];
      const [nx, ny] = [-uy, ux];
      const on = span(fly, 0.7 + 0.15 * k, 0.15);
      const l = (len / 2) * on;
      const pts: Pt[] = [[corner[0] - ux * l - nx * thick / 2, corner[1] - uy * l - ny * thick / 2], [corner[0] + ux * l - nx * thick / 2, corner[1] + uy * l - ny * thick / 2],
        [corner[0] + ux * l + nx * thick / 2, corner[1] + uy * l + ny * thick / 2], [corner[0] - ux * l + nx * thick / 2, corner[1] - uy * l + ny * thick / 2]];
      setQuad(q, at(pts, 0.8), [[0, 0], [1, 0], [1, 1], [0, 1]]);
    });
  }
  if (photoCard) {
    // the picture above the edge: whole until the blade, then lifted off the picture under it toward the lens, its far
    // side tipping up a little, and hinged away as the camera leaves
    const zz = lift + (10 + 22 * peel) * s;
    const angle = peel * 0.07 + leave * 1.75;
    setQuad(parts.above, hinge(q.above, zz, angle, leave * leave * 200 * s, beyond), q.above.map(uvOf));
    const top = within(q.above, bandTop, bandFoot);
    setQuad(parts.printAbove, hinge(top, zz + 0.4 * s, angle, leave * leave * 200 * s), top.map(uvOf));
    parts.mats.above.opacity = 1 - span(leave, 0.35, 0.5);
  } else {
    // the picture above the edge: whole until the blade, then peeled toward the lens
    setQuad(parts.above, hinge(q.above, lift + 10 * s, peel * 1.9, peel * peel * 260 * s, beyond), q.above.map(uvOf));
    const top = within(q.above, bandTop, bandFoot);
    setQuad(parts.printAbove, hinge(top, lift + 10.4 * s, peel * 1.9, peel * peel * 260 * s), top.map(uvOf));
    parts.mats.above.opacity = 1 - span(t, c.cut + 0.3, 0.3);
  }
  parts.mats.printAbove.opacity = parts.mats.above.opacity;
  const aboveBand = framed && q.above[3][1] > bandTop + 0.5;
  // the field: there from the blade on, hinged away as the camera leaves
  const fieldOn = photoCard ? 0 : span(t, c.cut, 0.06);
  const fieldAngle = leave * 1.75;
  setQuad(parts.field, hinge(q.field, lift + 6 * s, fieldAngle, leave * leave * 200 * s), q.field.map(() => [0, 0] as Pt));
  if (!photoCard) parts.mats.field.color.set(plan.colors[c.field] ?? c.field);
  parts.mats.field.opacity = fieldOn * (1 - span(leave, 0.35, 0.5));
  // the field's edge throws a soft shadow down onto the picture
  const band = 46 * s;
  const shadePts: Pt[] = [[q.field[3][0], q.field[3][1]], [q.field[2][0], q.field[2][1]], [q.field[2][0], q.field[2][1] + band / s], [q.field[3][0], q.field[3][1] + band / s]];
  setQuad(parts.shade, shadePts.map((p) => flown(toWorld(w(p), lift + 1.5 * s))), [[0, 1], [1, 1], [1, 0], [0, 0]]);
  parts.mats.shade.opacity = (photoCard ? 0.5 * peel : 0.32 * fieldOn) * (1 - leave);
  // the blade's gleam along the edge, bright as it crosses, then the light along the cut it leaves
  const g = span(t, c.cut, 0.12) * (1 - 0.78 * span(t, c.cut + 0.2, 0.5)) * (1 - leave);
  const thick = 2.2 * s;
  const along = span(t, c.cut, 0.25, bezier([0.3, 0, 0.2, 1]));
  const gl: Pt[] = [[0, c.line[0] - thick], [W * along, edgeY(c, W, W * along) - thick], [W * along, edgeY(c, W, W * along) + thick], [0, c.line[0] + thick]];
  setQuad(parts.gleam, gl.map((p) => flown(toWorld(w(p), lift + (photoCard ? 10 + 22 * peel + 2 : 12) * s))), [[0, 0], [1, 0], [1, 1], [0, 1]]);
  parts.mats.gleam.opacity = g;
  // the dark behind the type over a photograph that fills the frame, eased in from clear, gone with the card
  const scrimOn = c.scrim ? c.scrim[2] * (1 - leave) * span(t, c.arrive, 0.2) : 0;
  if (c.scrim) {
    // clear at the scrim's first coordinate, dark from its second on to the frame's edge beyond it: down the frame, or
    // across it toward the side the type's column stands on
    const [a, b] = [c.scrim[0], c.scrim[1]];
    const [x0, x1, y0, yb] = [-MARGIN * W, (1 + MARGIN) * W, -MARGIN * H, (1 + MARGIN) * H];
    const lay = (pts: Pt[]) => pts.map((p) => flown(toWorld(w(p), z + 0.9 * s)));
    if (c.scrim[3] === 'x') {
      const xe = a > b ? x0 : x1;
      setQuad(parts.scrim, lay([[a, y0], [b, y0], [b, yb], [a, yb]]), [[0, 1], [0, 0], [1, 0], [1, 1]]);
      setQuad(parts.dark, lay([[b, y0], [xe, y0], [xe, yb], [b, yb]]), [[0, 1], [1, 1], [1, 0], [0, 0]]);
    } else {
      setQuad(parts.scrim, lay([[x0, a], [x1, a], [x1, b], [x0, b]]), [[0, 1], [1, 1], [1, 0], [0, 0]]);
      setQuad(parts.dark, lay([[x0, b], [x1, b], [x1, yb], [x0, yb]]), [[0, 1], [1, 1], [1, 0], [0, 0]]);
    }
    parts.mats.scrim.opacity = scrimOn;
    parts.mats.dark.opacity = scrimOn;
  }
  // the keepsake is taped onto the page under the caption once the print has landed: slapped down from a little over
  // its size and turn, the tape pressed across its top as it lands; it goes with the card at the cut
  const kOn = c.keepsake && parts.keep ? span(t, c.arrive + KEEP_AT, KEEP_IN) : 0;
  const keepShown = kOn > 0 && leave < 0.001;
  if (keepShown && c.keepsake && parts.keep) {
    const K = parts.keep;
    const [x0, y0, x1, y1] = c.keepsake.box;
    const kmid: Pt = [(x0 + x1) / 2, (y0 + y1) / 2];
    const rest = 1 - bezier([0.2, 0.95, 0.3, 1])(kOn);
    const grow = 1 + 0.16 * rest;
    const angle = ((c.keepsake.turn + 4 * rest * Math.sign(c.keepsake.turn)) * Math.PI) / 180;
    const boxOf = (d: number): Pt[] => [[x0 - d, y0 - d], [x1 + d, y0 - d], [x1 + d, y1 + d], [x0 - d, y1 + d]];
    const placed = (pts: Pt[], dz: number) => turnedAbout(pts.map(([x, y]) => [kmid[0] + (x - kmid[0]) * grow, kmid[1] + (y - kmid[1]) * grow] as Pt), kmid, angle)
      .map((p) => flown(toWorld(w(p), z + (dz + 30 * rest) * s)));
    const [u0, v0, u1, v1] = c.keepsake.uv;
    const b = mount.border * (x1 - x0);
    setQuad(K.photo, placed(boxOf(0), 0.5), [[u0, 1 - v0], [u1, 1 - v0], [u1, 1 - v1], [u0, 1 - v1]]);
    setQuad(K.border, placed(boxOf(b), 0.45), [[0, 1], [1, 1], [1, 0], [0, 0]]);
    const shadowPts = boxOf(parts.kOut).map(([x, y]) => [x + 10 * rest, y + 18 * rest] as Pt);
    setQuad(K.lay, placed(shadowPts, 0.42), [[0, 1], [1, 1], [1, 0], [0, 0]]);
    (K.lay.mesh.material as THREE.MeshBasicMaterial).opacity = mount.shadow * (0.7 + 0.3 * rest);
    // the tape across the top's middle, a little crooked, pressed on as the print lands
    const press = span(kOn, 0.55, 0.45);
    const tw = (0.42 * (x1 - x0)) / 2 * (0.6 + 0.4 * press), th = 0.03 * H;
    const tm_: Pt = [kmid[0] + 0.08 * (x1 - x0), y0 - b * 0.4];
    const tpts = turnedAbout([[tm_[0] - tw, tm_[1] - th / 2], [tm_[0] + tw, tm_[1] - th / 2], [tm_[0] + tw, tm_[1] + th / 2], [tm_[0] - tw, tm_[1] + th / 2]], tm_,
      (-Math.sign(c.keepsake.turn) * 9 * Math.PI) / 180);
    setQuad(K.tape, placed(tpts, 0.8), [[0, 0], [1, 0], [1, 1], [0, 1]]);
    (K.tape.mesh.material as THREE.MeshBasicMaterial).opacity = 0.88 * press;
  }
  const casting = z > 3 || zFly > 3;
  parts.below.mesh.castShadow = casting;
  parts.above.mesh.castShadow = parts.mats.above.opacity > 0.5;
  parts.field.mesh.castShadow = casting && parts.mats.field.opacity > 0.5;
  // once in its slice the card takes the shadow of every card that floats over it
  const resting = leave > 0.999;
  if (resting) setQuad(parts.catch, belowPts.map((p) => toWorld(p, z + 0.8 * s)), belowPts.map(uvWall));
  parts.catch.mesh.receiveShadow = true;
  const order = index * 12;
  const layers: [Quad, number, boolean][] = [
    [parts.below, 0, true],
    [parts.dropTop, 1, !bordered && bandEdge && parts.mats.drop.opacity > 0.002],
    [parts.dropFoot, 1, !bordered && shown && parts.mats.drop.opacity > 0.002],
    [parts.lay, 1, bordered && parts.mats.lay.opacity > 0.002],
    [parts.border, 1.5, bordered],
    [parts.print, 2, shown],
    [parts.rimTop, 3, bandEdge && parts.mats.rim.opacity > 0.002],
    [parts.rimFoot, 3, shown && parts.mats.rim.opacity > 0.002],
    [parts.shade, 4, parts.mats.shade.opacity > 0.002],
    [parts.scrim, 4.5, scrimOn > 0.002],
    [parts.dark, 4.5, scrimOn > 0.002],
    [parts.field, 5, parts.mats.field.opacity > 0.002],
    [parts.above, 6, parts.mats.above.opacity > 0.002],
    [parts.printAbove, 7, aboveBand && parts.mats.above.opacity > 0.002],
    [parts.gleam, 8, g > 0.002],
    [parts.catch, 9, resting],
    ...parts.tapes.map((q) => [q, 10, bandEdge && fly > 0.7] as [Quad, number, boolean]),
    ...(parts.keep ? [[parts.keep.lay, 2.2, keepShown], [parts.keep.border, 2.4, keepShown], [parts.keep.photo, 2.6, keepShown],
      [parts.keep.tape, 10.5, keepShown]] as [Quad, number, boolean][] : []),
  ];
  return (
    <group>
      {layers.filter(([, , on]) => on).map(([q, k]) => {
        q.mesh.renderOrder = order + k;
        return <primitive key={q.mesh.uuid} object={q.mesh} />;
      })}
    </group>
  );
};
