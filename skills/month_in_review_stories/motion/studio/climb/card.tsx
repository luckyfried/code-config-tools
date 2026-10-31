// A moment's photograph on the wall, in two layers at their own depths: the print, the photograph on its band, and
// behind it the field, the same photograph carried past the band's edges, falling off to the ground: softened and dimmed
// on a dark ground, a pale print of itself on paper, so the whole card reads as a picture from the first frame. The
// print floats PRINT card px in front of the field and throws a soft shadow onto it; the field takes the print's light
// just past its edges, and the print's cut edges take the field's light: a light wrap. Over the hold the print eases
// about its subject against the camera's own move (LAYER) while the field holds still, and the camera's turn slides the
// two apart. When the camera leaves, the field fades and the print trims down to exactly its post's cell of the
// closer's wall, where it stays; a moment with no photograph fades as the camera leaves.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span, type Pt} from '../../system/three/motion';
import {distOf, flyAt, flyFrom, liftOf, onWall, PRINT, printZAt, trimAt, type Card, type Line, type Reel} from './plan';

export type Quad = {mesh: THREE.Mesh; geo: THREE.BufferGeometry};

export const quad = (mat: THREE.Material): Quad => {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(12), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(8), 2));
  geo.setIndex([0, 3, 1, 1, 3, 2]);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  return {mesh, geo};
};

export const setQuad = (q: Quad, pts: THREE.Vector3[], uvs: Pt[]) => {
  const pos = q.geo.getAttribute('position') as THREE.BufferAttribute;
  const uv = q.geo.getAttribute('uv') as THREE.BufferAttribute;
  pts.forEach((p, i) => pos.setXYZ(i, p.x, p.y, p.z));
  uvs.forEach((u, i) => uv.setXY(i, u[0], u[1]));
  pos.needsUpdate = true;
  uv.needsUpdate = true;
  q.geo.computeBoundingSphere();
};

// the photograph softened: nine taps of its coarser mip levels about uv, `r` apart (uv units)
const SOFT = `
  vec3 softAt(vec2 uv, vec2 r) {
    vec3 c = vec3(0.0);
    for (int i = -1; i <= 1; i++) for (int j = -1; j <= 1; j++) c += texture2D(map, uv + vec2(float(i), float(j)) * r, 4.0).rgb;
    return c / 9.0;
  }
  float boxOut(vec2 p, vec4 b) {
    vec2 d = max(vec2(b.x - p.x, b.y - p.y), vec2(p.x - b.z, p.y - b.w));
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
  }
`;

type Print = {edge: {value: THREE.Vector4}; wrap: {value: THREE.Vector2}};

/** The photograph as a print: drawn as it is, and within `wrap` (uv units, [u, v]) of the quad's own edges (`edge`: its
 * uv [left, bottom, right, top]) the photograph's softened light laid over its cut edge, so the edge reads lit. A
 * moment with no photograph is a print of `fill`, the ground its type stands on. */
export const bandMaterial = (texture: THREE.Texture | null, fill: string) => {
  const u: Print = {edge: {value: new THREE.Vector4(0, 0, 1, 1)}, wrap: {value: new THREE.Vector2(0.01, 0.01)}};
  if (!texture) return {m: new THREE.MeshBasicMaterial({color: fill, toneMapped: false, side: THREE.DoubleSide, transparent: true}), u};
  const m = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, side: THREE.DoubleSide, transparent: true});
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uEdge = u.edge;
    sh.uniforms.uWrap = u.wrap;
    sh.fragmentShader = 'uniform vec4 uEdge;\nuniform vec2 uWrap;\n' + sh.fragmentShader.replace('void main() {', SOFT + 'void main() {').replace(
      '#include <map_fragment>',
      `#include <map_fragment>
      {
        vec2 uv = vMapUv;
        vec2 e2 = min(uv - uEdge.xy, uEdge.zw - uv) / uWrap;
        float near = 1.0 - smoothstep(0.0, 1.0, min(e2.x, e2.y));
        vec3 glow = softAt(uv, uWrap * 0.8);
        diffuseColor.rgb = 1.0 - (1.0 - diffuseColor.rgb) * (1.0 - 0.7 * near * glow);
      }`,
    );
  };
  m.customProgramCacheKey = () => 'print';
  return {m, u};
};

type Field = {place: {value: THREE.Vector4}; band: {value: THREE.Vector4}; words: {value: THREE.Vector4}; hook: {value: THREE.Vector4};
  quad: {value: THREE.Vector4}; fill: {value: THREE.Color}; scrim: {value: number}; hookScrim: {value: number}};

/** The field: the photograph mirrored on past its own edges and falling off slowly to `fill` there, and fading out
 * toward the quad's edges, so it never ends in a hard edge. On a dark ground it is the photograph softened and dimmed;
 * on a paper ground it is the whole photograph, a little soft, raised toward white and laid in the paper's tone, a pale
 * print of itself around the band, so the card reads as a picture and never as bare or grey paper. Behind each line
 * of words the field goes back to the ground on a soft plate as the line lands, so the words stand on the ground
 * itself. Every rect is card px [x0, y0, x1, y1]: `place` the photograph laid over the card ([x, y, w, h]), `band` the
 * print it lies behind (its shadow falls down and to the right of it, its light spills just past its edges), `words`
 * where the words under the band stand and `hook` where the month's line stands (each plate comes in by `scrim` and
 * `hookScrim`, 0 to 1, as its words land and leave), `quad` the field's own extent. */
const fieldMaterial = (texture: THREE.Texture | null, fill: string) => {
  const u: Field = {place: {value: new THREE.Vector4(0, 0, 1, 1)}, band: {value: new THREE.Vector4()}, words: {value: new THREE.Vector4()},
    hook: {value: new THREE.Vector4()}, quad: {value: new THREE.Vector4()}, fill: {value: new THREE.Color(fill)}, scrim: {value: 0}, hookScrim: {value: 0}};
  if (!texture) return {m: new THREE.MeshBasicMaterial({color: fill, toneMapped: false, side: THREE.DoubleSide, transparent: true, depthWrite: false}), u};
  const m = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, side: THREE.DoubleSide, transparent: true, depthWrite: false});
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, {uPlace: u.place, uBand: u.band, uWords: u.words, uHook: u.hook, uQuad: u.quad, uFill: u.fill, uScrim: u.scrim,
      uHookScrim: u.hookScrim});
    sh.fragmentShader = 'uniform vec4 uPlace;\nuniform vec4 uBand;\nuniform vec4 uWords;\nuniform vec4 uHook;\nuniform vec4 uQuad;\nuniform vec3 uFill;\n'
      + 'uniform float uScrim;\nuniform float uHookScrim;\n'
      + sh.fragmentShader.replace('void main() {', SOFT + 'void main() {').replace(
        '#include <map_fragment>',
        `#include <map_fragment>
        {
          vec2 uv = vMapUv;
          vec2 p = vec2(uPlace.x + uv.x * uPlace.z, uPlace.y + (1.0 - uv.y) * uPlace.w);
          vec2 mirror = 1.0 - abs(1.0 - abs(uv));
          vec3 soft = softAt(mirror, vec2(26.0 / uPlace.z, 26.0 / uPlace.w));
          float past = boxOut(p, vec4(uPlace.xy, uPlace.xy + uPlace.zw));
          float paper = smoothstep(0.2, 0.6, dot(uFill, vec3(0.2126, 0.7152, 0.0722)));
          vec3 pale = mix(texture2D(map, mirror, 2.0).rgb, vec3(1.0), 0.3) * uFill;
          vec3 c = mix(uFill, mix(soft * 0.62, pale, paper), mix(0.9, 0.6, paper) * exp(-max(past, 0.0) / 420.0));
          c = mix(c, soft, mix(0.45, 0.2, paper) * exp(-max(boxOut(p, uBand), 0.0) / 16.0));
          float shade = 1.0 - smoothstep(-24.0, 70.0, boxOut(p - vec2(18.0, 34.0), uBand));
          c *= 1.0 - mix(0.62, 0.22, paper) * shade;
          float scrim = max(uScrim * (1.0 - smoothstep(-30.0, 60.0, boxOut(p, uWords))), uHookScrim * (1.0 - smoothstep(-30.0, 60.0, boxOut(p, uHook))));
          c = mix(c, uFill * mix(0.8, 1.0, paper), mix(0.55, 0.85, paper) * scrim);
          diffuseColor.rgb = c;
          diffuseColor.a *= smoothstep(0.0, 60.0, -boxOut(p, uQuad));
        }`,
      );
  };
  m.customProgramCacheKey = () => 'field';
  return {m, u};
};

/** How far the photograph is scaled about its subject at the far end of its ease: a push eases it back from LAYER to
 * 1 while the camera pushes in, a crane the same while the camera rises, a pull eases it in from 1 to LAYER while the
 * camera pulls back. */
const LAYER = 1.14;
const EASE = bezier([0.3, 0, 0.3, 1]);
/** How far past the card's frame the field reaches, as a share of it, so no turn of the camera shows its edge. */
const REACH = 1.3;

/** How a card stands off its landing while it flies in, `rest` from 1 (furthest) to 0 (landed), and how much of the
 * lens distance it starts from. The first card stands at its rest from the first frame; the others take three ways in
 * turn: rising square from below its cell, hinged flat about the line, or sliding in from the left. */
const entryOf = (index: number, rest: number, w: number, h: number) => {
  const m = new THREE.Matrix4();
  const axis = new THREE.Vector3(1, 0, 0);
  const up = new THREE.Vector3(0, 1, 0);
  const tilt = (about: THREE.Vector3, angle: number) => new THREE.Matrix4().makeRotationAxis(about, angle);
  if (index === 0) return {turn: m, near: 0};
  if (index % 3 === 1) return {turn: tilt(axis, rest * -1.45), near: 0.7};
  if (index % 3 === 2) return {turn: m.makeTranslation(-1.05 * w * rest, 0, 0).multiply(tilt(up, rest * 0.4)), near: 0.3};
  return {turn: m.makeTranslation(0, -0.75 * h * rest, 0).multiply(tilt(axis, rest * -0.6)), near: 0.4};
};

/** How far the field goes back to the ground behind a set of the card's lines at beat `t`, 0 to 1: coming in as the
 * first of them lands and going as the last has left, so no plate stays on the field without its words. */
const scrimAt = (c: Card, t: number, words: Line[]) => {
  if (!words.length) return 0;
  const from = Math.min(...words.map((ln) => ln.at ?? c.arrive));
  const to = Math.max(...words.map((ln) => ln.out ?? c.move[0]));
  return span(t, from - 0.1, 0.5) * (1 - span(t, to, 0.9));
};

export type SheetProps = {reel: Reel; card: Card; index: number; t: number; texture: THREE.Texture | null};

/** One moment's card. */
export const Sheet: React.FC<SheetProps> = ({reel: r, card: c, index, t, texture}) => {
  const {W, H} = r;
  const print = useMemo(() => bandMaterial(texture, r.colors.bg), [texture, r.colors.bg]);
  const field = useMemo(() => fieldMaterial(texture, r.colors.bg), [texture, r.colors.bg]);
  const qp = useMemo(() => quad(print.m), [print]);
  const qf = useMemo(() => quad(field.m), [field]);
  const {T, place, band} = c;
  const s = T.s;
  // the card flies in, landing a little past its rest and settling back; the print trims into its cell as the camera leaves
  if (t < flyFrom(r, index) - 0.01) return null;
  const fly = flyAt(r, index, t);
  const leave = trimAt(r, index, t);
  if (!c.stays && leave >= 1) return null;
  const lift = liftOf(s);
  const toWorld = (p: Pt, zz: number) => new THREE.Vector3(p[0] - W / 2, H / 2 - p[1], zz);
  // the card's middle on the wall, which the camera's station looks at: a layer behind the print is scaled up about it,
  // so it lands where the board placed it as seen from the station
  const mid: Pt = onWall(T, [W / 2, H / 2]);
  const about = (p: Pt, k: number): Pt => [mid[0] + (p[0] - mid[0]) * k, mid[1] + (p[1] - mid[1]) * k];
  const D = distOf(r);
  // the flight in
  const {turn, near} = entryOf(index, 1 - fly, W * s, H * s);
  const zFly = (1 - fly) * D * s * near;
  const pivot = toWorld([(c.cell[0] + c.cell[2]) / 2, (c.cell[1] + c.cell[3]) / 2], 0);
  const flown = (v: THREE.Vector3) => v.sub(pivot).applyMatrix4(turn).add(pivot).add(new THREE.Vector3(0, 0, zFly));
  // texture coordinates from card px through the photograph's place, scaled about its subject by `k`
  const e = EASE(clamp01((t - c.arrive) / Math.max(0.1, c.leave - c.arrive)));
  const k = c.hold === 'pull' ? lerp(1, LAYER, e) : lerp(LAYER, 1, e);
  const [fx, fy] = c.focus;
  const uvAt = (p: Pt, kk: number): Pt => [(fx + (p[0] - fx) / kk - place[0]) / place[2], 1 - (fy + (p[1] - fy) / kk - place[1]) / place[3]];
  const cardOf = (w: Pt): Pt => [(w[0] - T.o[0]) / s, (w[1] - T.o[1]) / s];

  // the print: the band's corners on the wall, trimmed to the post's cell as the camera leaves, at its depth over the
  // field, where the station's camera looks, so it fills the band exactly; it rests on the wall once it is in its cell
  const bandPts: Pt[] = [onWall(T, [0, band[0]]), onWall(T, [W, band[0]]), onWall(T, [W, band[1]]), onWall(T, [0, band[1]])];
  const slot: Pt[] = !c.stays ? bandPts : [[c.cell[0], c.cell[1]], [c.cell[2], c.cell[1]], [c.cell[2], c.cell[3]], [c.cell[0], c.cell[3]]];
  const pts = bandPts.map((p, i) => [lerp(p[0], slot[i][0], leave), lerp(p[1], slot[i][1], leave)] as Pt);
  const zp = printZAt(r, index, t);
  const uvs = pts.map((p) => uvAt(cardOf(p), k));
  setQuad(qp, pts.map((p) => flown(toWorld(p, zp))), uvs);
  print.u.edge.value.set(Math.min(uvs[0][0], uvs[3][0]), Math.min(uvs[2][1], uvs[3][1]), Math.max(uvs[1][0], uvs[2][0]), Math.max(uvs[0][1], uvs[1][1]));
  print.u.wrap.value.set(16 / place[2], 16 / place[3]);
  print.m.opacity = c.stays ? 1 : 1 - leave;
  qp.mesh.castShadow = zp > 3 || zFly > 3;
  qp.mesh.renderOrder = 10 + index * 10;

  // the field: the card's frame and REACH past it, at the card's lift behind the print, scaled up so its photograph
  // lines up with the print's from the station; it fades in with the flight and out as the print trims
  const lo: Pt = [W / 2 - (W / 2) * REACH, H / 2 - (H / 2) * REACH];
  const hi: Pt = [W / 2 + (W / 2) * REACH, H / 2 + (H / 2) * REACH];
  const corners: Pt[] = [lo, [hi[0], lo[1]], hi, [lo[0], hi[1]]];
  setQuad(qf, corners.map((p) => flown(toWorld(about(onWall(T, p), 1 + PRINT / D), lift))), corners.map((p) => uvAt(p, 1)));
  field.u.place.value.set(place[0], place[1], place[2], place[3]);
  field.u.band.value.set(0, band[0], W, band[1]);
  field.u.words.value.set(...c.strip);
  field.u.scrim.value = scrimAt(c, t, c.lines.filter((ln) => ln.name !== 'hook'));
  // the month's line: the card's width, from its ascenders to just under its baseline
  const hook = c.lines.filter((ln) => ln.name === 'hook');
  if (hook.length) field.u.hook.value.set(0, Math.min(...hook.map((ln) => ln.y - ln.size)), W, Math.max(...hook.map((ln) => ln.y + 0.35 * ln.size)));
  field.u.hookScrim.value = scrimAt(c, t, hook);
  field.u.quad.value.set(lo[0], lo[1], hi[0], hi[1]);
  field.m.opacity = (index === 0 ? 1 : fly) * (1 - leave);
  qf.mesh.renderOrder = 5 + index * 10;
  return (
    <group>
      {field.m.opacity > 0.001 ? <primitive object={qf.mesh} /> : null}
      <primitive object={qp.mesh} />
    </group>
  );
};
