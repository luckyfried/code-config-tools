// A post's print: their photograph in a paper border, standing dim in its tile of the wall until the camera comes for
// it. As the camera lands on it, it lifts out of the tile toward the lens, coming to light, a little past its station
// and back, its paper growing a label under or over the photograph for their words and the photograph taking its own
// proportions; through its hold it stands off the wall with its shadow on the wall under it, the key light across it
// and a light wrap along the photograph's edges, its tile behind it left as the wall's empty mount, and the photograph
// pushes in about its focal point at its own rate and moves against the paper as the camera moves (a still photograph's
// own motion; a generated clip, when one plays, takes the photograph's place). As the camera moves on it rises a hair,
// drops back into its tile and lands a hair under it and back, lit, one tile of the wall the film ends on.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span, type Pt} from '../../system/three/motion';
import type {Framing} from './camera';
import {timesOf, world, type Box, type Card, type Plan} from './plan';

/** Where a print rests once it is in its tile: a hair over the tiles before it. */
export const restZ = (index: number) => 0.03 * (index + 1);

/** How bright a print stands in its tile before the camera reaches it. */
const DIM = 0.42;

/** How bright the empty mount a print leaves in its tile stands, as a share of the dim prints' paper: a little under
 * them, so the tile reads as the wall's own recess for the print, never as a hole in the wall. */
const MOUNT = 0.75;

/** How much further than the camera the photograph inside a print pushes in through its time off the wall, and how far
 * it moves against the paper when the camera is a print's width away (shares of the photograph's window). */
const INNER = 0.06;
const PARALLAX = 0.05;

/** The shadow on the wall per wall px a print stands off it: its offset (the key light is above and to the left) and
 * the half width of its soft edge, and its darkness. */
const SHADOW_AT: Pt = [0.32, 0.5];
const SHADOW_SOFT = 0.25;
const SHADOW = 0.88;

/** The light wrap's band along the photograph's edges, a share of its shorter side, and its strength: the paper's
 * light spilling over the photograph's edge. */
const WRAP = 0.045;
const WRAP_ON = 0.22;

/** The rectangle a print covers at drop progress `e` (0 at its station, 1 in its tile; under 0 a little larger, over 1
 * a little smaller): its size changes by the same ratio every frame. */
export const rectAt = (c: Card, e: number): Box => {
  const [x0, y0, x1, y1] = c.rect;
  const [tx0, ty0, tx1, ty1] = c.tile;
  const w = (x1 - x0) * Math.pow((tx1 - tx0) / (x1 - x0), e);
  const h = (y1 - y0) * Math.pow((ty1 - ty0) / (y1 - y0), e);
  const cx = lerp((x0 + x1) / 2, (tx0 + tx1) / 2, clamp01(e));
  const cy = lerp((y0 + y1) / 2, (ty0 + ty1) / 2, clamp01(e));
  return [cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2];
};

/** The window of the photograph a `w` x `h` box shows at drop progress `e`, keeping the picture's own proportions:
 * pushed in by `zoom` (1 none) about the focal point, and moved by `drift` (shares of the window). */
const windowAt = (c: Card, w: number, h: number, e: number, zoom: number, drift: Pt): Box => {
  const k = w / h / c.aspect;
  const vw = Math.min(1, k) * zoom, vh = Math.min(1, 1 / k) * zoom;
  const [a0, b0, a1, b1] = c.uv0;
  const [u0, v0, u1, v1] = c.uv;
  const f = clamp01(e);
  const fu = c.focal[0], fv = 1 - c.focal[1];
  const uc = fu + (lerp((a0 + a1) / 2, (u0 + u1) / 2, f) - fu) * zoom + drift[0] * vw;
  const vc = fv + (lerp((b0 + b1) / 2, (v0 + v1) / 2, f) - fv) * zoom + drift[1] * vh;
  const ua = Math.min(1 - vw, Math.max(0, uc - vw / 2)), va = Math.min(1 - vh, Math.max(0, vc - vh / 2));
  return [ua, va, ua + vw, va + vh];
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

/** Sets a quad's corners (world; top left, top right, bottom right, bottom left) and their texture coordinates. */
const setQuad = (q: Quad, pts: THREE.Vector3[], uvs: Pt[]) => {
  const pos = q.geo.getAttribute('position') as THREE.BufferAttribute;
  const uv = q.geo.getAttribute('uv') as THREE.BufferAttribute;
  pts.forEach((p, i) => pos.setXYZ(i, p.x, p.y, p.z));
  uvs.forEach((u, i) => uv.setXY(i, u[0], u[1]));
  pos.needsUpdate = true;
  uv.needsUpdate = true;
};

/** A box drawn in nine patches, its edge band `b` wide on every side taking the outer half of its texture and its
 * middle the texture's center, so a soft edge keeps its width whatever the box's size. */
const nine = (mat: THREE.Material): Quad => {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(48), 3));
  const uv = [0, 0.5, 0.5, 1];
  geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(uv.flatMap((v) => uv.map((u) => [u, 1 - v])).flat()), 2));
  const idx: number[] = [];
  for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) {
    const a = r * 4 + c;
    idx.push(a, a + 4, a + 1, a + 1, a + 4, a + 5);
  }
  geo.setIndex(idx);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  return {mesh, geo};
};

/** Sets a nine-patch box: `box` in wall px with its band `b` wide straddling its edges (`inside` false) or inside
 * them, each point placed in the world by `at`. */
const setNine = (q: Quad, box: Box, b: number, at: (p: Pt) => THREE.Vector3, inside: boolean) => {
  const [x0, y0, x1, y1] = box;
  const out = inside ? 0 : b;
  const xs = [x0 - out, x0 + b, x1 - b, x1 + out];
  const ys = [y0 - out, y0 + b, y1 - b, y1 + out];
  const pos = q.geo.getAttribute('position') as THREE.BufferAttribute;
  ys.forEach((y, r) => xs.forEach((x, c) => {
    const v = at([x, y]);
    pos.setXYZ(r * 4 + c, v.x, v.y, v.z);
  }));
  pos.needsUpdate = true;
};

/** A soft texture for a nine-patch: `fill` is its alpha at (u, v), the band running from the edge (0) to the middle (0.5). */
const soft = (fill: (u: number, v: number) => number) => {
  const N = 64;
  const data = new Uint8Array(N * N * 4);
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const u = (x + 0.5) / N, v = (y + 0.5) / N;
    const i = (y * N + x) * 4;
    data[i] = data[i + 1] = data[i + 2] = 255;
    data[i + 3] = Math.round(255 * fill(Math.min(u, 1 - u), Math.min(v, 1 - v)));
  }
  const tex = new THREE.DataTexture(data, N, N);
  tex.magFilter = THREE.LinearFilter;
  tex.minFilter = THREE.LinearFilter;
  tex.needsUpdate = true;
  return tex;
};
const ramp = (d: number) => {
  const s = clamp01(d / 0.5);
  return s * s * (3 - 2 * s);
};
const SHADOW_TEX = soft((u, v) => ramp(u) * ramp(v));
const WRAP_TEX = soft((u, v) => Math.pow(1 - Math.min(ramp(u), ramp(v)), 2));

/** The key light across a print, multiplied into it: full light over its top left half, falling off toward its bottom
 * right. The film blends in linear light, where a veil of added white would lift every black, so the key only takes
 * light away. */
const keyTex = (() => {
  const cv = document.createElement('canvas');
  cv.width = cv.height = 64;
  const g = cv.getContext('2d')!;
  const grad = g.createLinearGradient(0, 0, 64, 64);
  grad.addColorStop(0, 'rgb(255,255,255)');
  grad.addColorStop(0.45, 'rgb(255,255,255)');
  grad.addColorStop(1, 'rgb(196,190,184)');
  g.fillStyle = grad;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(cv);
})();

/** The photograph's box in a print covering `r` at drop progress `e`: where it stands in the paper, as shares of the
 * paper's width and height, runs from where it stands at the station (over the label) to where it stands in the tile
 * (inside an even border). */
const photoAt = (c: Card, r: Box, e: number): Box => {
  const share = (b: Box, of: Box): Box => {
    const w = of[2] - of[0], h = of[3] - of[1];
    return [(b[0] - of[0]) / w, (b[1] - of[1]) / h, (b[2] - of[0]) / w, (b[3] - of[1]) / h];
  };
  const a = share(c.photo, c.rect), b = share(c.tilePhoto, c.tile);
  const f = clamp01(e);
  const w = r[2] - r[0], h = r[3] - r[1];
  return [r[0] + lerp(a[0], b[0], f) * w, r[1] + lerp(a[1], b[1], f) * h, r[0] + lerp(a[2], b[2], f) * w, r[1] + lerp(a[3], b[3], f) * h];
};

const cornersOf = (b: Box): Pt[] => [[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]]];
const uvsOf = (w: Box): Pt[] => [[w[0], w[3]], [w[2], w[3]], [w[2], w[1]], [w[0], w[1]]];
const FULL: Pt[] = [[0, 1], [1, 1], [1, 0], [0, 0]];

/** How a print tips while it lifts out, `rest` 0 in its tile and at its station and 1 halfway out: one of three tips
 * in turn, so no two prints in a row lift alike: back about its bottom edge, turned in from the days before it, or up
 * from below. */
const tipOf = (c: Card, rest: number) => {
  const X = new THREE.Vector3(1, 0, 0), Y = new THREE.Vector3(0, 1, 0);
  if (c.kind === 'hook') return {turn: new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rest * -0.3, rest * -0.25, rest * 0.06)), pivot: 'middle'};
  if (c.entry === 1) return {turn: new THREE.Matrix4().makeRotationAxis(X, rest * 0.3), pivot: 'bottom'};
  if (c.entry === 2) return {turn: new THREE.Matrix4().makeRotationAxis(Y, rest * 0.25), pivot: 'middle'};
  return {turn: new THREE.Matrix4().makeRotationAxis(X, rest * -0.25), pivot: 'middle'};
};

/** Where a print stands at `t`: its lift out of its tile and its drop back (the lift past its station and back, the drop
 * a hair up first and a hair under after), its drop progress `e`, how far off the wall it stands, the rectangle it
 * covers, its depth, and its tip about its pivot. */
export const poseOf = (plan: Plan, c: Card, index: number, t: number) => {
  const tm = timesOf(c);
  const lift = span(t, tm.rise[0], tm.rise[1], bezier(plan.ease.enter));
  const drop = span(t, tm.drop[0], tm.drop[1], bezier(plan.ease.drop));
  const out = t < tm.drop[0];
  const e = out ? 1 - lift : drop;
  const off = out ? clamp01(lift) : 1 - clamp01(drop);
  const r = rectAt(c, e);
  const rest = restZ(index);
  const z = lerp(rest, c.lift, off);
  const {turn, pivot} = tipOf(c, out ? Math.sin(Math.PI * clamp01(lift)) : 0);
  const pv = new THREE.Vector3(...world(plan, [(r[0] + r[2]) / 2, pivot === 'bottom' ? r[3] : (r[1] + r[3]) / 2], z));
  return {tm, e, off, r, rest, z, turn, pv};
};

/** The matrix that carries a point set on a print at its station to the same point of the print where it stands at
 * `t`, tipped with it, so the words on its label ride the print as it lifts out of the wall toward the lens. */
export const onPrint = (plan: Plan, c: Card, index: number, t: number) => {
  const {r, z, turn, pv} = poseOf(plan, c, index, t);
  const [x0, y0, x1, y1] = c.rect;
  const fit = new THREE.Matrix4().makeTranslation(r[0] - plan.W / 2, plan.H / 2 - r[1], z)
    .multiply(new THREE.Matrix4().makeScale((r[2] - r[0]) / (x1 - x0), (r[3] - r[1]) / (y1 - y0), 1))
    .multiply(new THREE.Matrix4().makeTranslation(plan.W / 2 - x0, y0 - plan.H / 2, -c.lift));
  return new THREE.Matrix4().makeTranslation(pv.x, pv.y, pv.z).multiply(turn).multiply(new THREE.Matrix4().makeTranslation(-pv.x, -pv.y, -pv.z))
    .multiply(fit);
};

export type CardProps = {plan: Plan; card: Card; index: number; t: number; texture: THREE.Texture; view: Framing; shadowZ: number};

export const CardView: React.FC<CardProps> = ({plan, card: c, index, t, texture, view, shadowZ}) => {
  const parts = useMemo(() => {
    const paper = new THREE.MeshBasicMaterial({color: plan.colors.paper, toneMapped: false, side: THREE.DoubleSide});
    const mount = new THREE.MeshBasicMaterial({color: new THREE.Color(plan.colors.paper).multiplyScalar(DIM * MOUNT), toneMapped: false});
    const photo = new THREE.MeshBasicMaterial({toneMapped: false, side: THREE.DoubleSide});
    const tr = {toneMapped: false, transparent: true, depthWrite: false};
    // a shadow darkens whatever it falls on, the plaster and the prints resting in it: the wall's own color brought
    // most of the way to black (the film blends in linear light, so a third of the color would still read as a glow)
    const shadow = new THREE.MeshBasicMaterial({map: SHADOW_TEX, color: new THREE.Color(plan.colors.ground).multiplyScalar(0.04), ...tr});
    const key = new THREE.MeshBasicMaterial({map: keyTex, ...tr, blending: THREE.CustomBlending, blendSrc: THREE.DstColorFactor,
      blendDst: THREE.ZeroFactor});
    const wrap = new THREE.MeshBasicMaterial({map: WRAP_TEX, color: new THREE.Color(1, 0.94, 0.86), blending: THREE.AdditiveBlending, ...tr});
    const gleam = new THREE.MeshBasicMaterial({color: new THREE.Color(1, 0.9, 0.7).multiplyScalar(4), blending: THREE.AdditiveBlending, ...tr});
    return {mount: quad(mount), paper: quad(paper), photo: quad(photo), shadow: nine(shadow), key: quad(key), wrap: nine(wrap), gleam: quad(gleam),
      mats: {paper, photo, shadow, wrap, gleam}};
  }, [plan]);
  parts.mats.photo.map = texture;
  const {tm, e, off, r, rest, z, turn, pv} = poseOf(plan, c, index, t);
  const lit = lerp(DIM, 1, span(t, tm.rise[0], 0.5 * tm.rise[1]));
  parts.mats.photo.color.setScalar(lit);
  parts.mats.paper.color.set(plan.colors.paper).multiplyScalar(lit);
  // the print tips as it lifts out, about its middle or its bottom edge, and lies flat in its tile and at its station
  const place = (p: Pt, dz = 0) => new THREE.Vector3(...world(plan, p, z + dz)).sub(pv).applyMatrix4(turn).add(pv);
  // the photograph stands in the paper where the station or the tile puts it; it pushes in and moves against the paper
  const ph = photoAt(c, r, e);
  const w = c.rect[2] - c.rect[0], h = c.rect[3] - c.rect[1];
  const inner = 1 - INNER * span(t, tm.rise[0], tm.drop[0] + tm.drop[1] - tm.rise[0], (u) => u);
  const dx = Math.max(-1, Math.min(1, (view.c[0] - (r[0] + r[2]) / 2) / w));
  const dy = Math.max(-1, Math.min(1, (view.c[1] - (r[1] + r[3]) / 2) / h));
  const win = windowAt(c, ph[2] - ph[0], ph[3] - ph[1], e, inner, [PARALLAX * dx * off, -PARALLAX * dy * off]);
  // the tile the print leaves stays the wall's mount for it, under the print whenever the print rests in it
  setQuad(parts.mount, cornersOf(c.tile).map((p) => new THREE.Vector3(...world(plan, p, rest - 0.02))), FULL);
  setQuad(parts.paper, cornersOf(r).map((p) => place(p)), FULL);
  setQuad(parts.photo, cornersOf(ph).map((p) => place(p, 0.05)), uvsOf(win));
  setQuad(parts.key, cornersOf(r).map((p) => place(p, 0.3)), FULL);
  // the shadow on the wall, offset and softened by the print's height over it
  const up = z - rest;
  setNine(parts.shadow, [r[0] + SHADOW_AT[0] * up, r[1] + SHADOW_AT[1] * up, r[2] + SHADOW_AT[0] * up, r[3] + SHADOW_AT[1] * up], 3 + SHADOW_SOFT * up,
    (p) => new THREE.Vector3(...world(plan, p, shadowZ)), false);
  parts.mats.shadow.opacity = SHADOW * clamp01(up / 30);
  // the light wrap along every edge of the photograph, strongest while the print stands in the light off the wall
  setNine(parts.wrap, ph, WRAP * Math.min(ph[2] - ph[0], ph[3] - ph[1]), (p) => place(p, 0.4), true);
  parts.mats.wrap.opacity = WRAP_ON * (0.35 + 0.65 * off) * lit;
  // a gleam along the tile's top as the print lands in it
  const g = span(t, tm.drop[0] + tm.drop[1] * 0.8, 0.08) * (1 - span(t, tm.drop[0] + tm.drop[1], 0.45));
  setQuad(parts.gleam, cornersOf([r[0], r[1] - 2.4, r[2], r[1] + 2.4]).map((p) => new THREE.Vector3(...world(plan, p, z + 1.5))), FULL);
  parts.mats.gleam.opacity = g;
  parts.mount.mesh.renderOrder = index * 10 - 1;
  parts.paper.mesh.renderOrder = index * 10;
  parts.photo.mesh.renderOrder = index * 10 + 1;
  parts.key.mesh.renderOrder = index * 10 + 2;
  parts.wrap.mesh.renderOrder = index * 10 + 3;
  parts.gleam.mesh.renderOrder = index * 10 + 5;
  parts.shadow.mesh.renderOrder = -5;
  return (
    <group>
      {off > 0.001 ? <primitive object={parts.mount.mesh} /> : null}
      <primitive object={parts.paper.mesh} />
      <primitive object={parts.photo.mesh} />
      {off > 0.001 ? <primitive object={parts.key.mesh} /> : null}
      <primitive object={parts.wrap.mesh} />
      {parts.mats.shadow.opacity > 0.002 ? <primitive object={parts.shadow.mesh} /> : null}
      {g > 0.002 ? <primitive object={parts.gleam.mesh} /> : null}
    </group>
  );
};
