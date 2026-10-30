// A moment's card on the wall: the photograph flies in whole as a print standing off the wall, its shadow on the wall
// beside it and the light wrapping its edges. Inside the print the picture lies at depths read from its focus point
// and its own line: the subject on the print's face, the picture rising past it toward the line and beyond falling
// back, the foreground under it standing a little forward. So as the camera arcs, the wall, the far part of the
// picture, the subject, the field of light under the type and the type standing proud of the print each pass the
// others at their own rate, and the print stays one picture, never cut. A streak of light runs along the line as the
// name rises out of it. The style card dresses the print: where its photo layout leaves a margin round the picture, the
// card is a page of the card's ground with the photograph pasted on it, inside its rim, turned by its tilt and held by
// its strips of tape. When the camera leaves, the print trims into its cell of the closer's wall and settles onto it.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, lerp, span, type Pt} from '../../system/three/motion';
import {onWall, paint, type Card, type Plan} from './plan';

export const cardScale = (c: Card) => c.T.s;
/** How far a card stands off the wall while it is the one the camera is on (world units), so the wall behind it moves
 * at its own rate as the camera arcs and the card's shadow lies on the wall beside it. */
export const liftOf = (c: Card) => 240 * c.T.s;
/** How far the field of light under the type and the type itself stand proud of the print (frame px). */
const FIELD = 50;
const PROUD = 120;
/** The world z the type stands at over its card. */
export const typeZ = (c: Card) => liftOf(c) + PROUD * c.T.s;
/** Where a card rests once it is in its cell: a hair over the cards before it. */
const restZ = (index: number) => 0.03 * (index + 1);
/** How far the print reaches past the frame, a share of the frame. */
const MARGIN = 0.03;
/** How far past the type's left and right the field of light under it fades to nothing (frame px), so the picture
 * changes its light under the type alone and a sun or a sky beside the words keeps its own. */
const FALL = 200;
/** How far down the field of light under the type (0 to 1) its lowest line may stand: the band holds near full to here
 * and falls off after. */
const DENSE = 0.68;
/** The light wrap: how wide its glow runs in from an edge (frame px), how strong it is while the card holds, and while
 * it moves. */
const WRAP = {width: 9, hold: 0.16, move: 0.55};
/** The picture's depth inside the print: how far behind the print's face its far side lies (frame px), how far forward
 * its foreground stands as a share of that, and how much of the picture the print shows about its focus point, so the
 * far side never slides past the photograph's edge. */
const DEEP = 300;
const NEAR = 0.45;
const SHOWN = 0.965;

/** The most a page shows round its photograph, a share of the frame's width, so the type standing inside the safe
 * area stays on the picture. */
const PAGE = 0.06;
/** A strip of tape: its length and width, shares of the frame's width, and how far it is turned off the print's top. */
const TAPE = {long: 0.17, wide: 0.045, turn: 38};

/** How far the photograph stands in from the card's edges (frame px): the margin the card's picture box leaves round it,
 * up to PAGE, and its rim inside that. None on a card whose picture runs to the frame's edges. */
export const insetOf = (plan: Plan) => {
  const {box, rim} = plan.photo.picture;
  const margin = Math.min(PAGE, Math.max(0, Math.min(box[0], 1 - box[0] - box[2])));
  return {margin: margin * plan.W, rim: margin > 0 ? rim * plan.W : 0};
};

/** Corners turned `deg` degrees clockwise about their middle. */
const turned = (pts: Pt[], deg: number): Pt[] => {
  const cx = (pts[0][0] + pts[2][0]) / 2, cy = (pts[0][1] + pts[2][1]) / 2, a = (deg * Math.PI) / 180;
  return pts.map(([x, y]) => [cx + (x - cx) * Math.cos(a) - (y - cy) * Math.sin(a), cy + (x - cx) * Math.sin(a) + (y - cy) * Math.cos(a)] as Pt);
};

/** A rectangle's corners grown `d` px on every side. */
const grown = (pts: Pt[], d: number): Pt[] => [[pts[0][0] - d, pts[0][1] - d], [pts[1][0] + d, pts[1][1] - d], [pts[2][0] + d, pts[2][1] + d], [pts[3][0] - d, pts[3][1] + d]];

/** The edge's y in the piece frame at x. */
const edgeY = (c: Card, W: number, x: number) => c.line[0] + ((c.line[1] - c.line[0]) * x) / W;

/** The print's corners in piece-frame px (in the order of its cell on the wall): the photograph as the frame shows it,
 * MARGIN past the frame where the photograph reaches that far. */
export const printOf = (c: Card, W: number, H: number): Pt[] => {
  const [px, py, pw, ph] = c.place;
  const x0 = Math.max(-MARGIN * W, px), x1 = Math.min((1 + MARGIN) * W, px + pw);
  const y0 = Math.max(-MARGIN * H, py), y1 = Math.min((1 + MARGIN) * H, py + ph);
  return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
};

/** The photograph's box in the card's frame, [x0, y0, x1, y1] px: the print, in from the card's edges by the card's
 * margin and rim where the card pastes it on a page. */
export const photoBoxOf = (plan: Plan, c: Card): [number, number, number, number] => {
  const full = printOf(c, plan.W, plan.H);
  const {margin, rim} = insetOf(plan);
  const into = margin > 0 ? margin + rim : 0;
  return [Math.max(into, full[0][0]), Math.max(into, full[0][1]), Math.min(plan.W - into, full[2][0]), Math.min(plan.H - into, full[2][1])];
};

/** The card's timings in beats. */
export const timesOf = (c: Card) => ({
  fly: c.hook ? [0, 0.3] : [c.arrive - 0.5, 0.75],
  leave: [c.leave - 0.6, 0.75],
});

/** How a card stands off its landing while it flies in, `rest` running from 1 (furthest) to 0 (landed), and how much
 * of the lens distance it starts from. The hook falls flat from the lens. Every other card takes its own line in the
 * way the board chose from its photograph (`entry`): hinged flat about its line (tipping the way the line climbs) for a
 * photograph taken on a tilt, sliding in along its line from its far end for a wide one, or rising square to its line
 * from below it. */
const entryOf = (c: Card, axis: THREE.Vector3, rest: number, w: number, h: number) => {
  const m = new THREE.Matrix4();
  if (c.hook) return {turn: m.makeRotationFromEuler(new THREE.Euler(rest * -0.5, rest * -0.45, rest * 0.12)), near: 0.82};
  const up = new THREE.Vector3(-axis.y, axis.x, 0);
  const tilt = (about: THREE.Vector3, angle: number) => new THREE.Matrix4().makeRotationAxis(about, angle);
  if (c.entry === 'hinge') return {turn: tilt(axis, rest * (c.line[1] < c.line[0] ? 1.45 : -1.45)), near: 0.7};
  if (c.entry === 'slide') {
    const from = axis.clone().multiplyScalar(-1.05 * w * rest);
    return {turn: m.makeTranslation(from.x, from.y, 0).multiply(tilt(up, rest * 0.4)), near: 0.3};
  }
  const from = up.clone().multiplyScalar(-0.75 * h * rest);
  return {turn: m.makeTranslation(from.x, from.y, 0).multiply(tilt(axis, rest * -0.6)), near: 0.4};
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

let band: THREE.Texture | null = null;
/** A vertical band, clear at its top and bottom and opaque through the middle, in white so the material's colour is the
 * colour it lays: black for the light taken out from under paper type, the paper for the veil under ink. */
const bandOf = () => {
  if (band) return band;
  const cv = document.createElement('canvas');
  cv.width = 4;
  cv.height = 256;
  const g = cv.getContext('2d')!;
  const lg = g.createLinearGradient(0, 0, 0, 256);
  lg.addColorStop(0, 'rgba(255,255,255,0)');
  lg.addColorStop(0.3, 'rgba(255,255,255,0.85)');
  lg.addColorStop(0.5, 'rgba(255,255,255,1)');
  lg.addColorStop(0.82, 'rgba(255,255,255,0.9)');
  lg.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = lg;
  g.fillRect(0, 0, 4, 256);
  band = new THREE.CanvasTexture(cv);
  return band;
};

/**
 * The print's picture at its depths: the photograph sampled where the camera's ray through a point of the print would
 * meet it lying `depth` behind the print's face, against where a camera square in front of the print would, so a
 * frontal view shows the photograph exactly and a turned one moves its far side against its near side. The depth runs
 * with the height in the picture from the focus point (0) to the line (`deep`), held there past the line, and forward
 * under the focus point to NEAR of it.
 */
type Depth = {u: THREE.Vector3; v: THREE.Vector3; n: THREE.Vector3; front: THREE.Vector3; focus: THREE.Vector2; line: THREE.Vector2; deep: number; shown: number};
const printMaterial = (texture: THREE.Texture) => {
  const d = {
    parU: {value: new THREE.Vector3(1, 0, 0)}, parV: {value: new THREE.Vector3(0, 1, 0)}, parN: {value: new THREE.Vector3(0, 0, 1)},
    parFront: {value: new THREE.Vector3(0, 0, 1000)}, parFocus: {value: new THREE.Vector2(0.5, 0.5)}, parLine: {value: new THREE.Vector2(0.6, 0.6)},
    parDeep: {value: 0}, parShown: {value: 1}, parNear: {value: NEAR},
  };
  const m = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, side: THREE.DoubleSide});
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, d);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vParWorld;')
      .replace('#include <project_vertex>', '#include <project_vertex>\nvParWorld = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
varying vec3 vParWorld;
uniform vec3 parU; uniform vec3 parV; uniform vec3 parN; uniform vec3 parFront;
uniform vec2 parFocus; uniform vec2 parLine; uniform float parDeep; uniform float parShown; uniform float parNear;
vec2 parSlide(vec3 eye, float depth) {
  vec3 ray = vParWorld - eye;
  float into = max(-dot(ray, parN), 1e-3);
  vec3 o = ray * (depth / into);
  o -= dot(o, parN) * parN;
  return vec2(dot(o, parU) / dot(parU, parU), dot(o, parV) / dot(parV, parV));
}`)
      .replace('#include <map_fragment>', THREE.ShaderChunk.map_fragment.replace('vec4 sampledDiffuseColor = texture2D( map, vMapUv );', `
float parL = mix(parLine.x, parLine.y, vMapUv.x);
float parK = (vMapUv.y - parFocus.y) / max(abs(parL - parFocus.y), 0.12);
float parDepth = parDeep * (parK >= 0.0 ? smoothstep(0.0, 1.0, parK) : -parNear * smoothstep(0.0, 1.0, -parK));
vec2 parUv = parFocus + (vMapUv - parFocus) * parShown + parSlide(cameraPosition, parDepth) - parSlide(parFront, parDepth);
vec4 sampledDiffuseColor = texture2D( map, parUv );`));
  };
  m.customProgramCacheKey = () => 'drive-print-depth';
  return {material: m, set: (p: Depth) => {
    d.parU.value.copy(p.u); d.parV.value.copy(p.v); d.parN.value.copy(p.n); d.parFront.value.copy(p.front);
    d.parFocus.value.copy(p.focus); d.parLine.value.copy(p.line); d.parDeep.value = p.deep; d.parShown.value = p.shown;
  }};
};

/** The light wrap over a quad laid with corner coordinates (0,0) (1,0) (1,1) (0,1): the light behind the card
 * glowing in along every edge of it in the card's burn light, `size` the quad's sides in frame px. */
const wrapMaterial = () => new THREE.ShaderMaterial({
  uniforms: {size: {value: new THREE.Vector2(1, 1)}, width: {value: WRAP.width}, color: {value: new THREE.Color()}, opacity: {value: 0}},
  vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: 'uniform vec2 size; uniform float width; uniform vec3 color; uniform float opacity; varying vec2 vUv; '
    + 'void main() { vec2 d = min(vUv, 1.0 - vUv) * size; float a = exp(-min(d.x, d.y) / width); gl_FragColor = vec4(color * a * opacity, 1.0); }',
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false,
});
/** The field of light under the type: the light taken out from under it (the ink) or, under ink, given to it (the
 * paper), over a quad laid with corner coordinates (0,1) (1,1) (1,0) (0,0): the band's profile down it, and across it
 * nothing at `reach.x`, full from `reach.y` to `reach.z` and nothing again at `reach.w`. */
const fieldMaterial = () => new THREE.ShaderMaterial({
  uniforms: {band: {value: bandOf()}, reach: {value: new THREE.Vector4(0, 0, 1, 1)}, color: {value: new THREE.Color(0, 0, 0)}, opacity: {value: 0}},
  vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: 'uniform sampler2D band; uniform vec4 reach; uniform vec3 color; uniform float opacity; varying vec2 vUv; '
    + 'void main() { float a = texture2D(band, vec2(0.5, vUv.y)).a * smoothstep(reach.x, reach.y, vUv.x) * (1.0 - smoothstep(reach.z, reach.w, vUv.x)); '
    + 'gl_FragColor = vec4(color, a * opacity); }',
  transparent: true, depthWrite: false, toneMapped: false,
});
const CORNERS: Pt[] = [[0, 0], [1, 0], [1, 1], [0, 1]];
const FLIPPED: Pt[] = [[0, 1], [1, 1], [1, 0], [0, 0]];
const sides = (pts: Pt[]) => new THREE.Vector2(Math.hypot(pts[1][0] - pts[0][0], pts[1][1] - pts[0][1]), Math.hypot(pts[3][0] - pts[0][0], pts[3][1] - pts[0][1]));

export type CardProps = {plan: Plan; card: Card; index: number; t: number; texture: THREE.Texture};

export const CardView: React.FC<CardProps> = ({plan, card: c, index, t, texture}) => {
  const {W, H} = plan;
  const parts = useMemo(() => {
    const print = printMaterial(texture);
    const field = fieldMaterial();
    const catcher = new THREE.ShadowMaterial({opacity: 0.45, transparent: true, depthWrite: false});
    const streak = new THREE.MeshBasicMaterial({color: new THREE.Color(plan.finish.burn).multiplyScalar(4), toneMapped: false, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending});
    const wrap = wrapMaterial();
    wrap.uniforms.color.value.set(plan.finish.burn);
    const page = new THREE.MeshBasicMaterial({color: paint(plan, plan.photo.ground), toneMapped: false, transparent: true, side: THREE.DoubleSide});
    const rim = new THREE.MeshBasicMaterial({color: paint(plan, plan.photo.picture.rimColor), toneMapped: false, transparent: true, side: THREE.DoubleSide});
    const tape = new THREE.MeshBasicMaterial({color: paint(plan, plan.photo.picture.tapeColor), toneMapped: false, transparent: true, depthWrite: false, side: THREE.DoubleSide});
    const q = {print: quad(print.material), field: quad(field), catcher: quad(catcher), streak: quad(streak), wrap: quad(wrap),
      page: quad(page), rim: quad(rim), tapes: [quad(tape), quad(tape)]};
    q.catcher.mesh.receiveShadow = true;
    q.page.mesh.castShadow = true;
    return {...q, depth: print.set, mats: {field, catcher, streak, wrap, page, rim, tape}};
  }, [texture, plan]);
  const tm = timesOf(c);
  const fly = span(t, tm.fly[0], tm.fly[1], bezier(plan.ease.enter));
  if (t < tm.fly[0] - 0.01) return null;
  const s = c.T.s;
  const lift = liftOf(c);
  const leave = span(t, tm.leave[0], tm.leave[1], bezier(plan.ease.move));
  const w = (p: Pt) => onWall(c.T, p);
  const toWorld = (p: Pt, z: number) => new THREE.Vector3(p[0] - W / 2, H / 2 - p[1], z);
  const [px, py, pw, ph] = c.place;
  // the line the name stands on, in world space: the axis the card flies in on and the hinges turn about
  const e0 = toWorld(w([0, c.line[0]]), 0);
  const e1 = toWorld(w([W, c.line[1]]), 0);
  const axis = e1.clone().sub(e0).normalize();
  // the card's flight: from toward the lens down onto its lift, taking its own line as it comes
  const D = (H * s) / 2 / Math.tan((30 * Math.PI) / 360);
  const {turn, near} = entryOf(c, axis, 1 - fly, W * s, H * s);
  // the card's ease may land it past its line and settle it back; it never passes through the wall
  const zFly = Math.max(0, 1 - fly) * D * near;
  const pivot = c.hook ? toWorld(w([W / 2, H / 2]), 0) : e0.clone().lerp(e1, 0.5);
  const flown = (v: THREE.Vector3) => v.sub(pivot).applyMatrix4(turn).add(pivot).add(new THREE.Vector3(0, 0, zFly));
  const z = lerp(lift, restZ(index), leave);
  // the whole print, trimmed toward its cell as the camera leaves; its texture coordinates come from the wall position
  // through the photograph's place, so the trim crops the picture and never squeezes it
  const full = printOf(c, W, H);
  // the photograph pasted on its page: in from the card's edges by the card's margin and rim, turned by its tilt while
  // the card is held, square again as it trims into its cell
  const {margin, rim} = insetOf(plan);
  const pasted = margin > 0;
  const into = margin + rim;
  const frame: Pt[] = pasted ? [[Math.max(into, full[0][0]), Math.max(into, full[0][1])], [Math.min(W - into, full[1][0]), Math.max(into, full[1][1])],
    [Math.min(W - into, full[2][0]), Math.min(H - into, full[2][1])], [Math.max(into, full[3][0]), Math.min(H - into, full[3][1])]] : full;
  const tilt = plan.photo.picture.tilt * (1 - leave);
  const square = frame.map(w).map((p, i) => [lerp(p[0], c.slot[i][0], leave), lerp(p[1], c.slot[i][1], leave)] as Pt);
  const pts = pasted ? turned(square, tilt) : square;
  const a = w([px, py]), b = w([px + pw, py + ph]);
  const uvOf = (p: Pt): Pt => [(p[0] - a[0]) / (b[0] - a[0]), 1 - (p[1] - a[1]) / (b[1] - a[1])];
  const corners = pts.map((p) => flown(toWorld(p, z)));
  setQuad(parts.print, corners, square.map(uvOf));
  // the page under it, the rim round it and the tape over its top corners go as the print trims into its cell
  const dressed = pasted ? 1 - span(leave, 0, 0.35) : 0;
  if (pasted) {
    const sheet = full.map(w).map((p, i) => [lerp(p[0], c.slot[i][0], leave), lerp(p[1], c.slot[i][1], leave)] as Pt);
    setQuad(parts.page, sheet.map((p) => flown(toWorld(p, z - 0.6 * s))), CORNERS);
    setQuad(parts.rim, turned(grown(square, rim * s), tilt).map((p) => flown(toWorld(p, z - 0.3 * s))), CORNERS);
    const r = turned(grown(square, rim * s), tilt);
    const long = TAPE.long * W * s, wide = TAPE.wide * W * s;
    [0, 1].forEach((k) => {
      const at = r[k];
      const deg = (k === 0 ? -TAPE.turn : TAPE.turn) + tilt;
      const strip: Pt[] = [[at[0] - long / 2, at[1] - wide / 2], [at[0] + long / 2, at[1] - wide / 2], [at[0] + long / 2, at[1] + wide / 2], [at[0] - long / 2, at[1] + wide / 2]];
      setQuad(parts.tapes[k], turned(strip, deg).map((p) => flown(toWorld(p, z + 0.9 * s))), CORNERS);
    });
    parts.mats.page.opacity = dressed;
    parts.mats.rim.opacity = dressed;
    parts.mats.tape.opacity = 0.82 * dressed;
  }
  // the picture's depths, in the print's own frame as it flies, holds and settles
  const U = corners[1].clone().sub(corners[0]).divideScalar(Math.max(1e-6, uvOf(pts[1])[0] - uvOf(pts[0])[0]));
  const V = corners[0].clone().sub(corners[3]).divideScalar(Math.max(1e-6, uvOf(pts[0])[1] - uvOf(pts[3])[1]));
  const n = U.clone().cross(V).normalize();
  const mid = corners[0].clone().add(corners[2]).multiplyScalar(0.5);
  const fx = (c.subject[0] + c.subject[2]) / 2, fy = (c.subject[1] + c.subject[3]) / 2;
  const vAt = (x: number) => 1 - (edgeY(c, W, x) - py) / ph;
  parts.depth({u: U, v: V, n, front: mid.clone().add(n.clone().multiplyScalar(D * 1.2)),
    focus: new THREE.Vector2((fx - px) / pw, 1 - (fy - py) / ph), line: new THREE.Vector2(vAt(px), vAt(px + pw)),
    deep: DEEP * s * (1 - leave), shown: lerp(SHOWN, 1, leave)});
  // the light wrapping the print's edges: strong while it flies and leaves, faint while it holds
  const moving = Math.max(1 - fly, Math.sin(Math.PI * leave));
  const wrap = lerp(WRAP.hold, WRAP.move, moving);
  setQuad(parts.wrap, pts.map((p) => flown(toWorld(p, z + 0.3 * s))), CORNERS);
  parts.mats.wrap.uniforms.size.value.copy(sides(frame));
  parts.mats.wrap.uniforms.opacity.value = wrap;
  // the print takes the shadow of the type standing over it
  setQuad(parts.catcher, pts.map((p) => flown(toWorld(p, z + 1.5 * s))), FLIPPED);
  parts.mats.catcher.opacity = 0.45 * (1 - leave);
  // the field of light under the type, standing between the print and the type: deepening once the name has landed
  const type = [...c.head, ...c.lines];
  const top = Math.min(...type.map((ln) => ln.y - ln.size * 0.95), c.line[0], c.line[1]) - 90;
  // the lowest type stands no lower than DENSE down the field, where the band is still near full, so the small line of
  // their words under the name keeps the shade over a pale sky as surely as the name does
  const low = Math.max(...type.map((ln) => ln.y + ln.size * 0.3), c.line[0], c.line[1]);
  const bottom = Math.max(low + 90, top + (low - top) / DENSE);
  const [tx0, tx1] = c.typeX;
  const x0 = Math.max(frame[0][0], tx0 - FALL), x1 = Math.min(frame[1][0], tx1 + FALL);
  const u = (x: number) => (x - x0) / Math.max(x1 - x0, 1);
  const box: Pt[] = [[x0, top], [x1, top], [x1, bottom], [x0, bottom]];
  setQuad(parts.field, box.map((p) => flown(toWorld(w(p), lift + FIELD * s))), FLIPPED);
  const field = parts.mats.field.uniforms;
  field.reach.value.set(u(tx0 - FALL), u(tx0), u(tx1), u(tx1 + FALL));
  field.color.value.set(c.type === 'ink' ? plan.colors.paper : plan.colors.ink);
  field.opacity.value = type.length ? Math.max(c.shade, plan.photo.line.scrim) * span(t, c.cut - 0.1, 0.4) * (1 - span(leave, 0, 0.4)) : 0;
  // the streak of light along the line, running out from its left end as the name rises and dying after
  const g = span(t, c.cut - 0.15, 0.12) * (1 - span(t, c.cut + 0.2, 0.45));
  const thick = 2.2 * s;
  const along = span(t, c.cut - 0.15, 0.3, bezier(plan.ease.move));
  const sx0 = frame[0][0], sx1 = lerp(sx0, frame[1][0], along);
  const line: Pt[] = [[sx0, edgeY(c, W, sx0) - thick], [sx1, edgeY(c, W, sx1) - thick], [sx1, edgeY(c, W, sx1) + thick], [sx0, edgeY(c, W, sx0) + thick]];
  setQuad(parts.streak, line.map((p) => flown(toWorld(w(p), lift + 2 * s))), CORNERS);
  parts.mats.streak.opacity = g;
  parts.print.mesh.castShadow = z > 3 || zFly > 3;
  parts.page.mesh.castShadow = pasted && (z > 3 || zFly > 3);
  // drawn back to front: the photograph and its wrap, the type's shadow on it, the streak, the field
  const order = index * 12;
  parts.page.mesh.renderOrder = order - 2;
  parts.rim.mesh.renderOrder = order - 1;
  parts.tapes.forEach((q) => { q.mesh.renderOrder = order + 5; });
  parts.print.mesh.renderOrder = order;
  parts.wrap.mesh.renderOrder = order + 1;
  parts.catcher.mesh.renderOrder = order + 2;
  parts.streak.mesh.renderOrder = order + 3;
  parts.field.mesh.renderOrder = order + 4;
  const on = leave < 0.999;
  return (
    <group>
      {dressed > 0.002 ? <primitive object={parts.page.mesh} /> : null}
      {dressed > 0.002 && rim > 0 ? <primitive object={parts.rim.mesh} /> : null}
      <primitive object={parts.print.mesh} />
      {dressed > 0.002 ? parts.tapes.slice(0, plan.photo.picture.tape).map((q, k) => <primitive key={k} object={q.mesh} />) : null}
      {wrap > 0.002 && on ? <primitive object={parts.wrap.mesh} /> : null}
      {on && t >= c.cut - 0.2 ? <primitive object={parts.catcher.mesh} /> : null}
      {g > 0.002 ? <primitive object={parts.streak.mesh} /> : null}
      {field.opacity.value > 0.002 ? <primitive object={parts.field.mesh} /> : null}
    </group>
  );
};
