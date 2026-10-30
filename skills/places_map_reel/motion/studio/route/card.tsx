// A stop's card on the map, laid out by the style card's photo layout: the card's ground over the whole frame, the
// photograph in its box (with its rim, its tilt, and its tape where the layout gives them, and shaded under the words
// where the layout asks), opening out of its pin toward the lens as the dot reaches the place; when the camera moves on
// the card folds down into a small print of the photograph beside the pin, standing off the map on its shadow, where it
// stays until the closer, which sinks every print back into its pin. While its place holds, the photograph moves
// inside its box: a slow push toward its focus, a drift the way the dot came, and the beat's move (the shared move's
// camera turns the picture inside its box, so the words the layout sets stand exactly where the board checked them).
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, type Pt} from '../../system/three/motion';
import type {Nudge} from '../../system/moves';
import {paper as sheet, SHEET} from './paper';
import {colorOf, liftOf, onWall, progressOf, timesOf, type Card, type Entry, type Plan} from './plan';

/** How far a print stands off the map once it rests: a hair over the prints before it. */
export const restZ = (index: number) => 16 + 0.3 * index;
/** The height a card opens out of on its pin. */
const PIN_Z = 0.6;
/** How far the photograph pushes in inside its box from the moment it opens to the end of its fold, toward a point
 * FOCUS of the way from the middle of its picture to its focus, and how far it drifts the way the dot came, as a share
 * of its box's width: the photograph's own motion while its place holds. */
const PUSH = 0.07;
const FOCUS = 0.5;
const DRIFT = 0.025;
/** The strips of tape at the photograph's top corners: their length and width as shares of the box's width, the angle
 * they cross the corner at, degrees, and how much of the picture shows through them. */
const TAPE: [number, number] = [0.2, 0.055];
const TAPE_DEG = 38;
const TAPE_ALPHA = 0.82;
/** The photograph's shadow on the ground under a rim: offset and spread as shares of the box's width, and its depth. */
const SHADOW: [number, number, number] = [0.012, 0.03, 0.32];
// where the card's ground starts to come up as the card opens, and over how much of the opening
const GROUND_IN: [number, number] = [0.35, 0.3];
/** The scrim under the words reaches this share of the frame's height above the words' first line, and stands at its
 * full depth from this share of the frame's height above that line, so the label over the line stands on it whole. */
const SCRIM_REACH = 0.12;
const SCRIM_HEAD = 0.035;
/** The least depth of a scrim the layout asks for, at its foot. */
const SCRIM_DEPTH = 0.86;
/** A hex color's luma, 0 to 1. */
const lumaOf = (hex: string) => {
  const c = new THREE.Color(hex);
  return 0.299 * c.r + 0.587 * c.g + 0.114 * c.b;
};

/** The beats each of the style card's arrivals takes; it ends as the stop's words come up, so the camera has come down
 * onto the page and the photograph lands on it in full view. */
const ENTRY: Record<Exclude<Entry, 'pin'>, number> = {'polaroid-drop': 0.8, 'tape-slap': 0.45, 'sticker-pop': 0.55, 'paper-slide': 0.65};
const dropEase = bezier([0.3, 1.35, 0.55, 1]);
const popEase = bezier([0.25, 1.7, 0.45, 1]);
const slideEase = bezier([0.15, 0.85, 0.3, 1]);

/** Where frame px `p` stands `u` (0 to 1) of the way through the card's arrival: the shift, turn and scale about the
 * box's middle each arrival draws, and how much of the photograph shows. */
const arrival = (entry: Exclude<Entry, 'pin'>, u: number, mid: Pt, W: number, H: number, west: boolean) => {
  let dx = 0, dy = 0, deg = 0, k = 1;
  if (entry === 'polaroid-drop') {
    // dropped from over the frame's top edge, swinging level as it lands a hair past its place and settles back
    dy = -(1 - dropEase(u)) * H;
    deg = -10 * (1 - u) * (1 - u);
    k = 1 + 0.05 * (1 - u);
  } else if (entry === 'tape-slap') {
    // brought down flat from near the lens, fast at the end, and a small jolt as it meets the page
    const a = clamp01(u / 0.72), b = clamp01((u - 0.72) / 0.28);
    k = 1 + 0.5 * (1 - a) * (1 - a) - 0.03 * Math.sin(Math.PI * b);
    deg = 6 * (1 - a);
  } else if (entry === 'sticker-pop') {
    // popped out of its middle past its size and back
    k = Math.max(0.001, popEase(u));
    deg = -7 * (1 - u);
  } else {
    // slid in from the side the dot came from, turning level as it comes to rest
    dx = (west ? 1 : -1) * (1 - slideEase(u)) * W * 1.1;
    deg = (west ? 4 : -4) * (1 - u);
  }
  const show = entry === 'tape-slap' ? clamp01(u * 6) : u > 0 ? 1 : 0;
  const a = (deg * Math.PI) / 180, cos = Math.cos(a), sin = Math.sin(a);
  return {show, at: (p: Pt): Pt => {
    const x = (p[0] - mid[0]) * k, y = (p[1] - mid[1]) * k;
    return [mid[0] + x * cos - y * sin + dx, mid[1] + x * sin + y * cos + dy];
  }};
};

type Quad = {mesh: THREE.Mesh; geo: THREE.BufferGeometry};

const quad = (mat: THREE.Material, colors = false): Quad => {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(12), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(8), 2));
  if (colors) geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(16), 4));
  geo.setIndex([0, 3, 1, 1, 3, 2]);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  return {mesh, geo};
};

const setQuad = (q: Quad, pts: THREE.Vector3[], uvs: Pt[]) => {
  const pos = q.geo.getAttribute('position') as THREE.BufferAttribute;
  const uv = q.geo.getAttribute('uv') as THREE.BufferAttribute;
  pts.forEach((p, i) => pos.setXYZ(i, p.x, p.y, p.z));
  uvs.forEach((u, i) => uv.setXY(i, u[0], u[1]));
  pos.needsUpdate = true;
  uv.needsUpdate = true;
  q.geo.computeBoundingSphere();
};

const UNIT: Pt[] = [[0, 0], [1, 0], [1, 1], [0, 1]];

/** A soft-edged square, the photograph's shadow on the card's ground. */
let softTex: THREE.Texture | null = null;
const soft = () => {
  if (softTex) return softTex;
  const N = 128, cv = document.createElement('canvas');
  cv.width = cv.height = N;
  const g = cv.getContext('2d')!;
  g.filter = `blur(${N * 0.08}px)`;
  g.fillStyle = '#000';
  g.fillRect(N * 0.18, N * 0.18, N * 0.64, N * 0.64);
  softTex = new THREE.CanvasTexture(cv);
  return softTex;
};

/** Turns frame px `p` by `deg` degrees clockwise about `c`. */
const turn = (p: Pt, c: Pt, deg: number): Pt => {
  if (!deg) return p;
  const a = (deg * Math.PI) / 180, dx = p[0] - c[0], dy = p[1] - c[1];
  return [c[0] + dx * Math.cos(a) - dy * Math.sin(a), c[1] + dx * Math.sin(a) + dy * Math.cos(a)];
};

/** The geometry the card's pieces share at beat `t`: how far it is open and folded, and the world point of a frame px.
 * A frame px maps onto the wall where the card stands whole and onto its print where it lies folded; the print shows
 * the photograph's box, so a point of the ground outside the box lands on the print's edge. */
export const cardSpace = (plan: Plan, c: Card, index: number, t: number, pulse = 1) => {
  const {W, H} = plan;
  const {opening, fold, sink} = progressOf(plan, c, t);
  const [x0, y0, x1, y1] = c.box;
  const lift = liftOf(c);
  const folding = fold > 0;
  const rest = folding ? restZ(index) : PIN_Z;
  const center = folding ? c.slot : c.pin;
  const grow = clamp01(opening * 4);
  const half = folding ? (c.size / 2) * pulse * (1 - sink) : (c.size / 2) * 0.02 * Math.max(0.02, grow);
  const aspect = (x1 - x0) / Math.max(1, y1 - y0);
  const hw = aspect >= 1 ? half : half * aspect, hh = aspect >= 1 ? half / aspect : half;
  const slotOf = (p: Pt, clamp: boolean): Pt => {
    let a = (p[0] - x0) / (x1 - x0), b = (p[1] - y0) / (y1 - y0);
    if (clamp) {
      a = clamp01(a);
      b = clamp01(b);
    }
    return [center[0] - hw + 2 * hw * a, center[1] - hh + 2 * hh * b];
  };
  const whole = Math.min(opening, 1 - fold);
  const z = lerp(rest, lift, whole);
  const toWorld = (p: Pt, zz: number) => new THREE.Vector3(p[0] - W / 2, H / 2 - p[1], zz);
  const at = (p: Pt, dz = 0, clamp = false) => {
    const w = onWall(c.T, p);
    const s = slotOf(p, clamp);
    return toWorld([lerp(s[0], w[0], whole), lerp(s[1], w[1], whole)], z + dz * Math.max(whole, 0.15));
  };
  // a card that arrives by one of the style card's moves stands at the lens's depth for the whole of its arrival, and
  // its ground still comes up out of the pin
  const entry = !folding && c.entry && c.entry !== 'pin' ? c.entry : null;
  if (!entry) return {W, H, x0, y0, x1, y1, opening, fold, sink, whole, z, lift, at, card: at, show: 1, toWorld};
  const tm = timesOf(c);
  const end = Math.max(tm.open[0] + 0.2, c.cutAt);
  const from = Math.max(tm.open[0], end - ENTRY[entry]);
  const arr = arrival(entry, clamp01((t - from) / Math.max(1e-6, end - from)), [(x0 + x1) / 2, (y0 + y1) / 2], W, H, Boolean(c.west));
  const card = (p: Pt, dz = 0) => toWorld(onWall(c.T, arr.at(p)), lift + dz * Math.max(whole, 0.15));
  return {W, H, x0, y0, x1, y1, opening, fold, sink, whole, z, lift, at, card, show: arr.show, toWorld};
};

/** The texture coordinates of the photograph at frame px `p`: the box's middle pushed toward the focus over the hold,
 * the beat's move turning the picture inside the box, the window held inside the photograph's own pixels. */
const photoUV = (plan: Plan, c: Card, t: number, nudge: Nudge) => {
  const [x0, y0, x1, y1] = c.box;
  const [px, py, pw, ph] = c.photo;
  const tm = timesOf(c);
  const held = clamp01((t - tm.open[0]) / Math.max(0.1, tm.fold[0] + tm.fold[1] - tm.open[0]));
  const mid: Pt = [(x0 + x1) / 2, (y0 + y1) / 2];
  const k = Math.min(1, (1 - PUSH * held) * (nudge.scale ?? 1));
  const bw = x1 - x0, bh = y1 - y0;
  const way = c.west ? -1 : 1;
  const want: Pt = [lerp(mid[0], c.focus[0], FOCUS * held) + (nudge.dx ?? 0) * bh + DRIFT * held * bw * way, lerp(mid[1], c.focus[1], FOCUS * held) + (nudge.dy ?? 0) * bh];
  const w = k * bw, h = k * bh;
  const center: Pt = [Math.min(px + pw - w / 2, Math.max(px + w / 2, want[0])), Math.min(py + ph - h / 2, Math.max(py + h / 2, want[1]))];
  const roll = ((nudge.roll ?? 0) * 180) / Math.PI;
  return (p: Pt): Pt => {
    const q = turn([center[0] + (p[0] - mid[0]) * k, center[1] + (p[1] - mid[1]) * k], center, roll);
    return [(q[0] - px) / pw, 1 - (q[1] - py) / ph];
  };
};

export type CardProps = {plan: Plan; card: Card; index: number; t: number; texture: THREE.Texture; pulse: number; nudge: Nudge};

export const CardView: React.FC<CardProps> = ({plan, card: c, index, t, texture, pulse, nudge}) => {
  const lay = plan.layout;
  const parts = useMemo(() => {
    const flat = (color: string, extra: THREE.MeshBasicMaterialParameters = {}) =>
      new THREE.MeshBasicMaterial({color, toneMapped: false, side: THREE.DoubleSide, ...extra});
    // every part of a card is drawn in the transparent pass, so it sorts by its order among the route and the dot drawn
    // over the map, and covers them
    const photo = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, side: THREE.DoubleSide, transparent: true});
    const ground = flat(colorOf(plan, lay.ground), {transparent: true, depthWrite: false, ...(plan.grain > 0 ? {map: sheet()} : {})});
    // the paper's sheet is a little under white, so a grained ground is lifted back to its own color
    if (plan.grain > 0) ground.color.multiplyScalar(1.07);
    const rim = flat(colorOf(plan, lay.picture.rim > 0 ? lay.picture.rimColor : 'paper'), {transparent: true, polygonOffset: true, polygonOffsetFactor: 2, polygonOffsetUnits: 8});
    const shade = new THREE.MeshBasicMaterial({map: soft(), color: '#000', transparent: true, depthWrite: false, toneMapped: false, opacity: SHADOW[2]});
    const tape = flat(colorOf(plan, lay.picture.tapeColor), {transparent: true, opacity: TAPE_ALPHA, depthWrite: false});
    const scrim = new THREE.MeshBasicMaterial({vertexColors: true, transparent: true, depthWrite: false, toneMapped: false, side: THREE.DoubleSide});
    return {photo: quad(photo), ground: quad(ground), rim: quad(rim), shade: quad(shade), tapes: [quad(tape), quad(tape)], scrim: quad(scrim, true), scrimFoot: quad(scrim, true), mats: {ground}};
  }, [texture, plan, lay]);
  if (t < timesOf(c).open[0] - 0.01) return null;
  const k = cardSpace(plan, c, index, t, pulse);
  if (k.fold >= 1 && k.sink >= 1) return null;
  const {W, H, x0, y0, x1, y1, at, card} = k;
  const s = c.s;
  const bw = x1 - x0;
  const mid: Pt = [(x0 + x1) / 2, (y0 + y1) / 2];
  const tilt = lay.picture.tilt;
  const boxPts: Pt[] = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
  const tilted = boxPts.map((p) => turn(p, mid, tilt));
  const uv = photoUV(plan, c, t, k.whole > 0.5 ? nudge : {});
  setQuad(parts.photo, tilted.map((p) => card(p, 0.6 * s)), boxPts.map(uv));
  (parts.photo.mesh.material as THREE.MeshBasicMaterial).opacity = k.show;
  // the ground over the whole frame while the card stands whole; folded, it is the print's border
  const b = plan.closer.paper * W * (1 - k.whole);
  const framePts: Pt[] = [[0, 0], [W, 0], [W, H], [0, H]];
  setQuad(parts.ground, framePts.map((p) => at(p, -0.6 * s, true)), framePts.map((p) => [(p[0] * s) / SHEET, (-p[1] * s) / SHEET] as Pt));
  // the ground comes up as the card opens past a third, so the map stays in view behind the print as it lifts off
  parts.mats.ground.opacity = clamp01((k.whole - GROUND_IN[0]) / GROUND_IN[1]);
  const r = lay.picture.rim * W;
  const rimPts: Pt[] = [[x0 - r - b, y0 - r - b], [x1 + r + b, y0 - r - b], [x1 + r + b, y1 + r + b], [x0 - r - b, y1 + r + b]].map((p) => turn(p as Pt, mid, tilt));
  const showRim = r > 0 || k.whole < 0.999;
  if (showRim) setQuad(parts.rim, rimPts.map((p) => card(p, 0.2 * s)), UNIT);
  (parts.rim.mesh.material as THREE.MeshBasicMaterial).opacity = k.show;
  const sh = SHADOW[1] * bw;
  const shPts: Pt[] = [[x0 - r - sh, y0 - r - sh], [x1 + r + sh, y0 - r - sh], [x1 + r + sh, y1 + r + sh], [x0 - r - sh, y1 + r + sh]]
    .map((p) => turn([p[0] + SHADOW[0] * bw, p[1] + 1.6 * SHADOW[0] * bw] as Pt, mid, tilt));
  const showShade = r > 0 && k.whole > 0.02;
  if (showShade) setQuad(parts.shade, shPts.map((p) => card(p, -0.3 * s)), UNIT);
  (parts.shade.mesh.material as THREE.MeshBasicMaterial).opacity = SHADOW[2] * k.whole * k.show;
  // the tape across the top corners, a strip at each, crossing it inward
  const tapes = Math.min(2, Math.round(lay.picture.tape));
  const tl = TAPE[0] * bw, tw = TAPE[1] * bw;
  [[x0 - r, y0 - r, -TAPE_DEG], [x1 + r, y0 - r, TAPE_DEG]].slice(0, tapes).forEach(([cx, cy, deg], j) => {
    const pts: Pt[] = [[cx - tl / 2, cy - tw / 2], [cx + tl / 2, cy - tw / 2], [cx + tl / 2, cy + tw / 2], [cx - tl / 2, cy + tw / 2]];
    setQuad(parts.tapes[j], pts.map((p) => card(turn(turn(p, [cx, cy], deg), mid, tilt), 1.2 * s)), UNIT);
    (parts.tapes[j].mesh.material as THREE.MeshBasicMaterial).opacity = TAPE_ALPHA * k.show;
  });
  // the scrim: the photograph shaded from clear well above the words to the shade's depth a little above the words'
  // first line (the label's, where there is one), and at that depth from there to its foot, so every line of the words
  // stands on the whole of it; the shade is black under light words and the card's paper under dark ones, and never
  // lighter than SCRIM_DEPTH, so the words read over the brightest part of any photograph
  const scrim = (lay.line.scrim > 0 ? Math.max(lay.line.scrim, SCRIM_DEPTH) : 0) * k.whole * k.show;
  if (scrim > 0.002) {
    const first = c.lines.length ? Math.max(y0, Math.min(...c.lines.map((ln) => ln.y - ln.size * 1.1))) : y1;
    const words = Math.max(y0, first - SCRIM_HEAD * H);
    const top = Math.max(y0, words - SCRIM_REACH * H);
    const ink = c.lines.length ? colorOf(plan, c.lines[c.lines.length - 1].color) : colorOf(plan, 'paper');
    const col = new THREE.Color(lumaOf(ink) > 0.5 ? '#000000' : colorOf(plan, 'paper'));
    const shadeQuad = (q: Quad, a: number, b: number, from: number) => {
      const pts: Pt[] = [[x0, a], [x1, a], [x1, b], [x0, b]];
      setQuad(q, pts.map((p) => card(p, 0.9 * s)), UNIT);
      const tint = q.geo.getAttribute('color') as THREE.BufferAttribute;
      [from, from, scrim, scrim].forEach((v, i) => tint.setXYZW(i, col.r, col.g, col.b, v));
      tint.needsUpdate = true;
    };
    shadeQuad(parts.scrim, top, words, 0);
    shadeQuad(parts.scrimFoot, words, y1, scrim);
  }
  // a print casts its shadow on the map where the card has a finish to cast it in (a flat style draws no shadow, as its
  // map slab casts none); the ground is the frame's own page and casts none
  const casting = plan.grain > 0 && (k.fold > 0.05 || k.whole > 0.05);
  parts.photo.mesh.castShadow = casting;
  parts.ground.mesh.castShadow = false;
  parts.rim.mesh.castShadow = casting;
  // the card the camera is on draws over every print; a print draws over the prints before it
  const order = (k.whole > 0.001 ? 500 : 0) + index * 10;
  parts.ground.mesh.renderOrder = order;
  parts.shade.mesh.renderOrder = order + 1;
  parts.rim.mesh.renderOrder = order + 2;
  parts.photo.mesh.renderOrder = order + 3;
  parts.scrim.mesh.renderOrder = order + 4;
  parts.scrimFoot.mesh.renderOrder = order + 4;
  parts.tapes.forEach((q) => (q.mesh.renderOrder = order + 5));
  return (
    <group>
      {k.whole > 0.001 ? <primitive object={parts.ground.mesh} /> : null}
      {showShade && k.show > 0 ? <primitive object={parts.shade.mesh} /> : null}
      {showRim && k.show > 0 ? <primitive object={parts.rim.mesh} /> : null}
      {k.show > 0 ? <primitive object={parts.photo.mesh} /> : null}
      {scrim > 0.002 ? <primitive object={parts.scrim.mesh} /> : null}
      {scrim > 0.002 ? <primitive object={parts.scrimFoot.mesh} /> : null}
      {(k.show > 0 ? parts.tapes.slice(0, tapes) : []).map((q, j) => <primitive key={j} object={q.mesh} />)}
    </group>
  );
};
