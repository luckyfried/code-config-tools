// One of the next posts, in one of three moves. `close`: the whole photograph tips up onto the station, the frame
// closes onto its subject, and the rest of the picture falls back behind the crop as a field of its own, dimming and
// going out of focus, while the crop pushes slowly in on the recorded focus point; past the photograph's edges the
// field carries on as its own mirror image, always out of focus, so the picture never shows an edge. `slide`: the 3:4
// cell slides in along the wall from the left of the grid's first cell on the curve the row steps along on, so it
// pushes the row along as it seats in the frame waiting there. `drop`: the 3:4 cell falls from above the view into the
// frame waiting on the grid's first cell. A crop held at the station draws back and drops into the grid, turning into
// its 3:4 cell on the way, while its field closes in on it and goes under it; the wall takes it over where it lands.
// Every card is opaque from its first frame, casts its shadow on the wall (the crop on its own field too; a falling cell
// once it is near the wall), and carries the light wrap on its cut edges, except where it lies flat on its page's paper.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span, type Pt} from '../../system/three/motion';
import {ARC, easeOf, frameAt} from './frame';
import {closedAt} from './page';
import {toWorld, type Box, type Plan, type Post} from './plan';
import {cornersOf, quad, rimMaterial, setQuad, setRim, UNIT, uvCorners, type Quad} from './quad';
import {reflowOf} from './wall';

const WALL_Z = 1.5;
// how far the field falls back behind the crop as the frame closes, and further over the hold, px
const RECEDE = [60, 50];
// the field's brightness once the frame has closed
const DIM = 0.3;
// how far the crop pushes in on the focus point over the hold, a share of its width
const PUSH_IN = 0.05;
// the light wrap's strength and width, a share of the card's shorter side
const WRAP = 0.55;
const WRAP_W = 0.07;
// how far the field carries on past each edge of the photograph, a share of the photograph's size
const SPREAD = 1;
// how soft the field is once the frame has closed, 0 to 1; past the photograph's edges it is always this soft
const SOFT = 0.75;
// how long the field takes to close in on the crop, beats, from just before the crop draws back
const IRIS = 0.55;
// where a falling cell sets off, a share of the camera's distance off the wall
const FALL = 0.12;
// the share of a falling cell's fall after which it casts its shadow on the wall
const SHADOW_FROM = 0.66;

// the field's picture: the photograph mirrored past its edges, sampled over a disc and from a coarser level of its
// mipmaps as `blur` rises, and drawn at `spread` opacity past its edges
const FIELD = /* glsl */ `
#ifdef USE_MAP
  vec2 raw = vMapUv;
  float past = max(max(-raw.x, raw.x - 1.0), max(-raw.y, raw.y - 1.0));
  float b = max(blur, ${SOFT.toFixed(2)} * smoothstep(0.0, 0.1, past));
  vec2 gx = dFdx(raw) * exp2(b * 5.0);
  vec2 gy = dFdy(raw) * exp2(b * 5.0);
  vec4 acc = vec4(0.0);
  for (int i = 0; i < 12; i++) {
    float a = float(i) * 2.3999632;
    vec2 q = raw + vec2(cos(a), sin(a)) * sqrt((float(i) + 0.5) / 12.0) * b * 0.03;
    acc += textureGrad(map, 1.0 - abs(1.0 - mod(q, 2.0)), gx, gy);
  }
  diffuseColor *= acc / 12.0;
  diffuseColor.a *= mix(1.0, spread, smoothstep(0.0, 0.03, past));
#endif
`;

const fieldMaterial = (texture: THREE.Texture) => {
  const m = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, transparent: true, depthWrite: false, side: THREE.DoubleSide});
  const u = {blur: {value: 0}, spread: {value: 0}};
  m.onBeforeCompile = (s) => {
    Object.assign(s.uniforms, u);
    s.fragmentShader = 'uniform float blur;\nuniform float spread;\n' + s.fragmentShader.replace('#include <map_fragment>', FIELD);
  };
  return {m, u};
};

const about = (o: THREE.Vector3, r: THREE.Matrix4) =>
  new THREE.Matrix4().makeTranslation(o.x, o.y, o.z).multiply(r).multiply(new THREE.Matrix4().makeTranslation(-o.x, -o.y, -o.z));

/** A uv rect scaled about a point by `k`. */
const toward = (uv: number[], f: Pt, k: number) => [f[0] + (uv[0] - f[0]) * k, f[1] + (uv[1] - f[1]) * k, f[0] + (uv[2] - f[0]) * k, f[1] + (uv[3] - f[1]) * k];

export const PostView: React.FC<{plan: Plan; post: Post; index: number; t: number; texture: THREE.Texture}> = ({plan, post: p, index, t, texture}) => {
  const parts = useMemo(() => {
    const field = fieldMaterial(texture);
    // the crop's shadow on its field: a pane just in front of the field that shows only the shadow falling on it
    const shade = quad(new THREE.ShadowMaterial({opacity: 0.5, transparent: true, depthWrite: false}));
    shade.mesh.receiveShadow = true;
    // the card is drawn among the transparent things so a falling one can draw over the frame, and is always opaque
    const crop = quad(new THREE.MeshBasicMaterial({map: texture, toneMapped: false, transparent: true, side: THREE.DoubleSide}));
    return {crop, field: quad(field.m), soft: field.u, shade, rim: quad(rimMaterial(plan.light))};
  }, [texture]);
  const tm = p.times;
  if (t < tm.fly[0] - 0.01 || t >= tm.seat) return null;
  const order = 100 + index * 10;
  const D = (plan.H * 0.7) / 2 / Math.tan((30 * Math.PI) / 360);
  const show = (q: Quad, on: boolean) => (q.mesh.visible = on);
  const card = (pts: THREE.Vector3[], w: number, h: number, wrap: number) => {
    setRim(parts.rim, pts.map((v) => v.clone().setZ(v.z + 0.6)), wrap, WRAP_W * Math.min(w, h), w, h);
    parts.rim.mesh.renderOrder = parts.crop.mesh.renderOrder + 1;
  };
  const cm = parts.crop.mesh.material as THREE.MeshBasicMaterial;
  cm.depthTest = true;
  parts.crop.mesh.renderOrder = order + 2;
  parts.crop.mesh.castShadow = true;
  parts.field.mesh.renderOrder = order;
  parts.shade.mesh.renderOrder = order + 1;
  const node = (
    <group>
      <primitive object={parts.field.mesh} />
      <primitive object={parts.shade.mesh} />
      <primitive object={parts.crop.mesh} />
      <primitive object={parts.rim.mesh} />
    </group>
  );
  const [sx, sy, sw, sh] = p.slot;

  if (p.move !== 'close') {
    show(parts.field, false);
    show(parts.shade, false);
    let box: Box, z: number, spin = new THREE.Matrix4();
    if (p.move === 'drop') {
      // the cell falls from above the view onto slot 0, turning out of a small spin, and lands in slot 0 as the frame
      // lands round it; it draws over the frame while it is nearer the lens than the frame, and under its bars after
      const u = span(t, tm.fly[0], tm.fly[1], bezier(easeOf(plan).fall));
      const [fx, fy] = p.from ?? [sx + sw / 2, sy - 2 * sh];
      box = [lerp(fx - sw / 2, sx, u), lerp(fy - sh / 2, sy, u), sw, sh];
      z = lerp(FALL * D, WALL_Z, u);
      const mid = new THREE.Vector3(...toWorld(plan, [box[0] + sw / 2, box[1] + sh / 2], z));
      spin = about(mid, new THREE.Matrix4().makeRotationZ(p.side * 0.22 * (1 - u)));
      const above = z > frameAt(plan, t).z;
      // its shadow falls on the wall only over the last third of the fall: higher up it lands far below the card, on
      // wall the view shows while the card is still above it, a gray card with nothing casting it
      parts.crop.mesh.castShadow = u > SHADOW_FROM;
      cm.depthTest = !above;
      parts.crop.mesh.renderOrder = above ? 990 : order + 2;
    } else {
      // the cell slides in along the wall from one step left of slot 0, on the curve the row steps along on over the
      // same beats, so it pushes the row; it lifts off the wall as the row's cells do and settles flat as it seats
      const u = span(t, tm.fly[0], tm.fly[1], bezier(reflowOf(plan)));
      const step = plan.grid.cw + plan.grid.g;
      box = [sx - step * (1 - u), sy, sw, sh];
      z = WALL_Z + Math.sin(Math.PI * clamp01(u)) * 18;
    }
    const pts = cornersOf(box).map((q) => new THREE.Vector3(...toWorld(plan, q, z)).applyMatrix4(spin));
    setQuad(parts.crop, pts, uvCorners(p.uv34));
    card(pts, sw, sh, WRAP);
    return node;
  }

  const fly = span(t, tm.fly[0], tm.fly[1], bezier(easeOf(plan).land));
  const close = span(t, tm.close[0], tm.close[1], bezier(easeOf(plan).close));
  // the crop parts from its field as the frame reaches it: the field dims, softens and falls back, and the crop's
  // edges light, late in the close, so the crop never shows apart from the picture while the frame is still round the whole
  const shut = close ** 3;
  const holdLen = Math.max(1e-3, tm.drop[0] - (tm.close[0] + tm.close[1]));
  const hold = span(t, tm.close[0] + tm.close[1], holdLen, (v) => v);
  const drop = span(t, tm.drop[0], tm.drop[1], bezier(easeOf(plan).drop));
  const iris = span(t, tm.drop[0] - 0.1, IRIS, bezier(easeOf(plan).close));
  const [wx, wy, ww, wh] = p.whole;
  const [cx, cy, cw, ch] = p.crop;
  const rest = 1 - fly;
  // the move in: the whole photograph tips up off its bottom edge out of the lens
  const pivot = new THREE.Vector3(...toWorld(plan, [wx + ww / 2, wy + wh], p.z));
  const m = about(pivot, new THREE.Matrix4().makeRotationX(rest * 1.2));
  const lens = new THREE.Vector3(0, 0, rest * D * 0.25);
  const flown = (v: THREE.Vector3) => v.applyMatrix4(m).add(lens);
  // the crop: at the station, pushing in on the focus point over the hold, then drawing back and dropping into slot 0,
  // its 4:5 turning into the 3:4 cell
  const box: Box = [lerp(cx, sx, drop), lerp(cy, sy, drop), lerp(cw, sw, drop), lerp(ch, sh, drop)];
  const held = toward(p.uvSubject, p.uvFocal, 1 - PUSH_IN * hold);
  const uv = held.map((v, i) => lerp(v, p.uv34[i], clamp01(drop))) as [number, number, number, number];
  const dist = Math.hypot(sx - cx + (sw - cw) / 2, sy - cy + (sh - ch) / 2);
  const z = lerp(p.z, WALL_Z, drop) + Math.sin(Math.PI * clamp01(drop)) * ARC * dist;
  const cropPts = cornersOf(box).map((q) => flown(new THREE.Vector3(...toWorld(plan, q, z))));
  setQuad(parts.crop, cropPts, uvCorners(uv));
  // the crop is a card of its own once the frame has closed on it, and a print lying flat on the paper while its page
  // stands round it
  const paper = p.page ? closedAt(p.page, t, bezier(plan.ease.move)) : 0;
  card(cropPts, box[2], box[3], WRAP * shut * (1 - 0.6 * clamp01(drop)) * (1 - paper));
  // the field: the whole photograph behind its crop, falling back from it, dimming and softening as the frame closes;
  // as the crop draws back it closes in on the crop's place, picture and depth, and goes under it
  if (iris >= 0.999) {
    show(parts.field, false);
    show(parts.shade, false);
    return node;
  }
  show(parts.field, true);
  show(parts.shade, true);
  const back = lerp(p.z - 2 - RECEDE[0] * shut - RECEDE[1] * hold, z - 2, iris);
  const focus = new THREE.Vector3(...toWorld(plan, [box[0] + box[2] / 2, box[1] + box[3] / 2], back));
  // the field recedes about the crop's center, so the subject stays put while the picture round it falls away
  const k = (z - back) / D;
  const ext = [wx - SPREAD * ww, wy - SPREAD * wh, ww * (1 + 2 * SPREAD), wh * (1 + 2 * SPREAD)];
  const fbox = ext.map((v, i) => lerp(v, box[i], iris)) as Box;
  const fuv = [-SPREAD, -SPREAD, 1 + SPREAD, 1 + SPREAD].map((v, i) => lerp(v, uv[i], iris)) as [number, number, number, number];
  const fieldPts = cornersOf(fbox).map((q) => {
    const v = new THREE.Vector3(...toWorld(plan, q, back));
    return flown(v.sub(focus).multiplyScalar(1 + k).add(focus));
  });
  setQuad(parts.field, fieldPts, uvCorners(fuv));
  const away = shut * (1 - iris);
  parts.soft.blur.value = SOFT * away;
  parts.soft.spread.value = fly * fly * (1 - iris);
  (parts.field.mesh.material as THREE.MeshBasicMaterial).color.setScalar(lerp(1, DIM, away));
  parts.field.mesh.castShadow = false;
  setQuad(parts.shade, fieldPts.map((v) => v.clone().setZ(v.z + 0.5)), UNIT);
  parts.shade.geo.computeVertexNormals();
  (parts.shade.mesh.material as THREE.ShadowMaterial).opacity = 0.5 * away;
  return node;
};
