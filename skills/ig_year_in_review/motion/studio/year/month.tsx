// A month's photograph on the wall, where the card stands it: a full frame, a print standing off its own soft field
// (the same photograph, blurred and dimmed, behind it) with a soft shadow under it; a picture in a box of the frame,
// laid flat in that box on the card's ground; or no picture at all, the card's ground alone under the words. It opens
// out of its own line as the camera comes to it, over the month before, or is there whole from the moment of a cut
// that jumps, and the dot draws along that line; the line stays where the card asks for it. While it is open the photograph is two layers
// split on its line: the near one (the photograph over the line, with the month's words on their plate, and the accent
// line on its cut), which stands in front and slides against the far one under the camera's move, its cut catching the
// light and casting a shadow, and the far one (the photograph under the line, and the slit of the photograph over it);
// the two are back together by the moment the month is left. When the month is done the photograph's two halves and its
// field close down onto the line while the line, with the slit of the photograph around it, levels and slides into the
// month's row, then the slit spreads across the wall into the row's band, from the month's name to the spine, the
// accent line staying on it. Every month but the last does this under the next month's photograph. The photograph is one
// surface at a time and always at its own exposure: the whole card until the halves take it over, then the halves; its
// edges catch the light.
import {useMemo} from 'react';
import * as THREE from 'three';
import {cutOf} from '../../system/moves';
import {bezier, lerp, span, type Pt} from '../../system/three/motion';
import {layerOf, lineY, liftOf, onWall, restZ, type Month, type Plan} from './plan';

/** How far past the piece frame's edges the slit and the halves run, as a fraction of the frame. */
export const REACH = 0.06;

/** The slit's half thickness while the photograph is open, piece px: a hair under the accent line, until it widens to
 * the month's band as the halves close. */
const HAIR = 6;

/** A month's field: its photograph blurred and dimmed to `FIELD_DIM` of its light behind the print, this many times the
 * piece frame each way. */
export const FIELD = 1.8;
const FIELD_DIM = 0.45;

/** The print's shadow on its field: how far it falls (right and down, from the key light at the upper left) and how
 * soft it is, piece px, and how dark. */
const DROP: Pt = [40, 64];
const DROP_SOFT = 70;
const DROP_DARK = 0.6;

/** The near layer's shadow on the far one, as dark as this at the layers' widest. */
const CUT_DARK = 0.5;

export type Quad = {mesh: THREE.Mesh; geo: THREE.BufferGeometry};

/** Where each corner lies across the surface, clockwise from the top left: an edge at 0 or 1 catches the light, a side
 * whose two corners share 0.5 does not. Soft boxes and fields read it as the surface's own coordinates. */
export const WHOLE: Pt[] = [[0, 0], [1, 0], [1, 1], [0, 1]];

/** No edge catches the light: a picture lying flat in the card's box, its halves meeting with no cut between them. */
const FLAT: Pt[] = [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]];

export const quad = (mat: THREE.Material): Quad => {
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(12), 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(new Float32Array(8), 2));
  geo.setAttribute('edge', new THREE.BufferAttribute(new Float32Array(WHOLE.flat()), 2));
  geo.setIndex([0, 3, 1, 1, 3, 2]);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.frustumCulled = false;
  return {mesh, geo};
};

/** Sets a quad's corners (world, clockwise from the top left), their texture coordinates and, when given, which of its
 * edges catch the light. */
export const setQuad = (q: Quad, pts: THREE.Vector3[], uvs: Pt[], edges?: Pt[]) => {
  const pos = q.geo.getAttribute('position') as THREE.BufferAttribute;
  const uv = q.geo.getAttribute('uv') as THREE.BufferAttribute;
  pts.forEach((p, i) => pos.setXYZ(i, p.x, p.y, p.z));
  uvs.forEach((u, i) => uv.setXY(i, u[0], u[1]));
  pos.needsUpdate = true;
  uv.needsUpdate = true;
  if (edges) {
    const e = q.geo.getAttribute('edge') as THREE.BufferAttribute;
    edges.forEach((u, i) => e.setXY(i, u[0], u[1]));
    e.needsUpdate = true;
  }
  q.geo.computeBoundingSphere();
};

const withEdge = (sh: {vertexShader: string; fragmentShader: string}) => {
  sh.vertexShader = sh.vertexShader
    .replace('#include <common>', '#include <common>\nattribute vec2 edge;\nvarying vec2 vEdge;')
    .replace('#include <begin_vertex>', '#include <begin_vertex>\nvEdge = edge;');
  sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec2 vEdge;');
};

/** A photograph's material whose edges catch the light: the warm key light wraps several px in from each edge, as it
 * does round a print that stands off a wall, and round the cut of the near layer. */
export const lit = (mat: THREE.MeshBasicMaterial) => {
  mat.onBeforeCompile = (sh) => {
    withEdge(sh);
    sh.fragmentShader = sh.fragmentShader.replace('#include <opaque_fragment>', `
        vec2 px = min(vEdge, 1.0 - vEdge) / max(fwidth(vEdge), vec2(1e-5));
        outgoingLight = mix(outgoingLight, vec3(1.1, 1.05, 0.99), 0.5 * exp(-min(px.x, px.y) / 6.0));
        #include <opaque_fragment>`);
  };
  mat.customProgramCacheKey = () => 'lit-edges';
  return mat;
};

/** A photograph blurred and dimmed to `dim` of its light, its edges fading over `fade` of the surface: a month's field
 * and the wall's ground. */
export const blurred = (dim: number, fade: number) => {
  const mat = new THREE.MeshBasicMaterial({toneMapped: false, transparent: fade > 0});
  mat.color.setScalar(dim);
  mat.onBeforeCompile = (sh) => {
    withEdge(sh);
    sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>', `
        vec4 acc = vec4(0.0);
        for (int i = 0; i < 24; i++) {
          float a = float(i) * 2.39996;
          float r = sqrt((float(i) + 0.5) / 24.0) * 0.03;
          acc += texture2D(map, vMapUv + vec2(cos(a), sin(a)) * r, 2.0);
        }
        diffuseColor *= acc / 24.0;
        vec2 e = min(vEdge, 1.0 - vEdge);
        diffuseColor.a *= ${fade > 0 ? `smoothstep(0.0, ${fade.toFixed(3)}, min(e.x, e.y))` : '1.0'};`);
  };
  mat.customProgramCacheKey = () => `blurred-${fade}`;
  return mat;
};

/** A flat box in `color` with rounded corners and edges that fade, sized each frame by `setBox`: the plates under type
 * and the soft shadows. */
export const softBox = (color: string) => {
  const mat = new THREE.MeshBasicMaterial({color, toneMapped: false, transparent: true, depthWrite: false});
  const box = {value: new THREE.Vector4(1, 1, 0, 1)};
  mat.userData.box = box;
  mat.onBeforeCompile = (sh) => {
    withEdge(sh);
    sh.uniforms.uBox = box;
    sh.fragmentShader = sh.fragmentShader
      .replace('varying vec2 vEdge;', 'varying vec2 vEdge;\nuniform vec4 uBox;')
      .replace('#include <alphatest_fragment>', `
        vec2 q = abs(vEdge - 0.5) * uBox.xy - (0.5 * uBox.xy - uBox.w - uBox.z);
        float d = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - uBox.z;
        diffuseColor.a *= 1.0 - smoothstep(-uBox.w, uBox.w, d);
        #include <alphatest_fragment>`);
  };
  mat.customProgramCacheKey = () => 'soft-box';
  return mat;
};

/** A soft box's size (`w` by `h`, the quad's own px), corner radius and how far its edge fades, inside the quad. */
export const setBox = (mat: THREE.Material, w: number, h: number, r: number, soft: number) =>
  (mat.userData.box.value as THREE.Vector4).set(Math.max(1, w), Math.max(1, h), r, soft);

/** When a month's photograph opens out of its line, [from, length] in beats: at once, on the moment of the cut, where
 * the cut into it jumps. */
export const openingOf = (plan: Plan, index: number): Pt => {
  const m = plan.months[index];
  return index === 0 || cutOf(m.transition ?? undefined)?.jump ? [m.start - 0.02, 0.02] : m.at.card;
};

/** How far the halves have closed onto the line: open at 0, shut at 1. */
const foldOf = (m: Month, t: number) => span(t, m.at.fold[0], m.at.fold[1], bezier([0.45, 0, 0.3, 1]));

export type MonthProps = {plan: Plan; month: Month; index: number; t: number; texture: THREE.Texture};

export const MonthView: React.FC<MonthProps> = ({plan, month: m, index, t, texture}) => {
  const {W, H} = plan;
  const parts = useMemo(() => {
    const mat = () => lit(new THREE.MeshBasicMaterial({map: texture, toneMapped: false, transparent: true, side: THREE.DoubleSide}));
    const card = lit(new THREE.MeshBasicMaterial({map: texture, toneMapped: false}));
    const flat = (color: string) => new THREE.MeshBasicMaterial({color, toneMapped: false, transparent: true});
    // a full frame stands off its photograph blurred; a picture in a box, or none, lies on the card's ground
    const bleeds = m.full && m.picture !== null;
    const field = bleeds ? blurred(FIELD_DIM, 0.06) : flat(plan.colors[plan.photo.ground] ?? plan.colors.bg);
    if (bleeds) field.map = texture;
    return {
      band: quad(mat()), above: quad(mat()), below: quad(mat()), card: quad(card), rule: quad(flat(plan.colors.accent)),
      field: quad(field), drop: quad(softBox('#000000')), cut: quad(softBox('#000000')),
    };
  }, [texture, plan.colors, plan.photo.ground, m.full, m.picture]);
  const a = m.at;
  const [from, opening] = openingOf(plan, index);
  if (t < from) return null;
  const s = m.T.s;
  const toWorld = (p: Pt, z: number) => new THREE.Vector3(p[0] - W / 2, H / 2 - p[1], z);
  const w = (p: Pt) => onWall(m.T, p);
  const layer = layerOf(plan, m, t);
  const near = (p: Pt) => onWall(layer.T, p);
  const [px, py, pw, ph] = m.place;
  // a picture in the card's box stands still on its box while the photograph pushes in inside it, about its focus, over
  // the month's hold (4%, 7% on the story's peak): the box's edges stay where the card's grid and its moves' mats meet them
  const pushed = m.full ? 0 : (m.peak ? 0.07 : 0.04) * span(t, a.arrive, Math.max(0.1, a.pull[0] - a.arrive), bezier([0.3, 0, 0.6, 1]));
  const fu = m.focus[0], fv = 1 - m.focus[1];
  const uvOf = (p: Pt): Pt => {
    const u = (p[0] - px) / pw, v = 1 - (p[1] - py) / ph;
    return [fu + (u - fu) * (1 - pushed), fv + (v - fv) * (1 - pushed)];
  };
  // the picture's edges: the card's box, or REACH past the frame on a full frame
  const pic = m.picture;
  const shown = pic !== null;
  const x0 = Math.max(px, m.full || !pic ? -REACH * W : pic[0]), x1 = Math.min(px + pw, m.full || !pic ? (1 + REACH) * W : pic[2]);
  const part = span(t, a.part[0], a.part[1], bezier([0.2, 0.8, 0.3, 1]));
  const slide = span(t, a.slide[0], a.slide[1], bezier(plan.ease.move));
  const lift = liftOf(m);
  const z = lerp(lift, restZ(index), slide);
  const y = (x: number) => lineY(m, W, x);
  const fold = foldOf(m, t);
  // how far the print and its field stand open about the line: they open out of it as the camera comes to the month
  // and close down onto it with the halves
  const on = t < a.open[0] ? span(t, from, opening, bezier(plan.ease.move)) : 1 - fold;
  const openAbout = (pts: Pt[], k = on) => pts.map(([fx, fy]): Pt => [fx, y(fx) + (fy - y(fx)) * k]);
  // the field: the photograph blurred and dimmed, FIELD times the frame about its middle, the frame's own part of the
  // photograph spread over it; it opens out of the line twice as fast as the print, so the month before is covered
  // edge to edge before the print has half opened
  const c: Pt = [W / 2, H / 2];
  const fieldPts = openAbout([[c[0] - FIELD * c[0], c[1] - FIELD * c[1]], [c[0] + FIELD * c[0], c[1] - FIELD * c[1]],
    [c[0] + FIELD * c[0], c[1] + FIELD * c[1]], [c[0] - FIELD * c[0], c[1] + FIELD * c[1]]], Math.min(1, 2 * on));
  setQuad(parts.field, fieldPts.map((p) => toWorld(w(p), lift - 1)),
    fieldPts.map((p) => uvOf([c[0] + (p[0] - c[0]) / FIELD, c[1] + (p[1] - c[1]) / FIELD])));
  parts.field.mesh.visible = on > 0.002;
  parts.field.mesh.renderOrder = 97 + index * 10;
  // the print's soft shadow on its field, falling right and down from the key light; the print runs REACH past the
  // piece frame, as far as the photograph reaches
  const top = Math.max(py, m.full || !pic ? -REACH * H : pic[1]), bottom = Math.min(py + ph, m.full || !pic ? (1 + REACH) * H : pic[3]);
  const frame: Pt[] = [[x0, top], [x1, top], [x1, bottom], [x0, bottom]];
  const opened = openAbout(frame);
  const grow = [[-1, -1], [1, -1], [1, 1], [-1, 1]];
  const dropPts = opened.map((p, i): Pt => [p[0] + DROP[0] + grow[i][0] * DROP_SOFT, p[1] + DROP[1] + grow[i][1] * DROP_SOFT]);
  setQuad(parts.drop, dropPts.map((p) => toWorld(w(p), lift - 0.8)), WHOLE);
  setBox(parts.drop.mesh.material as THREE.Material, x1 - x0 + 2 * DROP_SOFT,
    Math.max(1, opened[3][1] - opened[0][1]) + 2 * DROP_SOFT, 0, DROP_SOFT);
  (parts.drop.mesh.material as THREE.MeshBasicMaterial).opacity = DROP_DARK * Math.min(1, on * 2);
  // a print standing off its field casts its shadow; a picture laid flat in its box does not
  parts.drop.mesh.visible = on > 0.002 && m.full && shown;
  parts.drop.mesh.renderOrder = 98 + index * 10;
  // the month's photograph at its own exposure, standing off the wall: it opens out of its own line as the camera
  // comes to it, its top and its foot uncovered outward from the line, and the dot draws its line across it until the
  // halves take it over
  const cardOn = t < a.open[0] ? on : 0;
  setQuad(parts.card, opened.map((p) => toWorld(w(p), lift - 2 * s)), opened.map(uvOf), m.full ? WHOLE : FLAT);
  parts.card.mesh.visible = cardOn > 0.002 && shown;
  parts.card.mesh.castShadow = cardOn > 0.5;
  parts.card.mesh.renderOrder = 99 + index * 10;
  if (t < a.part[0]) {
    return (
      <group>
        <primitive object={parts.field.mesh} />
        <primitive object={parts.drop.mesh} />
        <primitive object={parts.card.mesh} />
      </group>
    );
  }
  // the slit is a hair under the accent line while the photograph is open, and widens to the month's band as the
  // halves close onto it
  const bh = part * lerp(HAIR, m.band, span(t, a.fold[0] - 0.6, 0.6));
  // the slit runs on under the near layer by as far as the near layer can slide off it
  const under = (0.3 * layer.sep) / s;
  // the slit: the photograph seen through the parted line, then leveled and slid into the row
  const r = m.row;
  const half = m.band * s;
  const slot: Pt[] = [[r.x0, r.y - half], [r.x1, r.y - half], [r.x1, r.y + half], [r.x0, r.y + half]];
  const reach = Math.min(pw, (r.x1 - r.x0) / s);
  const cx = Math.min(px + pw - reach / 2, Math.max(px + reach / 2, W / 2));
  const mid = y(cx);
  const strip: Pt[] = [[cx - reach / 2, mid - m.band], [cx + reach / 2, mid - m.band], [cx + reach / 2, mid + m.band], [cx - reach / 2, mid + m.band]];
  const open: Pt[] = [[x0, y(x0) - bh - under], [x1, y(x1) - bh - under], [x1, y(x1) + bh], [x0, y(x0) + bh]];
  // the band: the slit spread across the wall, showing the photograph's whole width in a slit around its line
  const spread = span(t, a.slide[0] + a.slide[1] - 0.05, 0.5, bezier(plan.ease.move));
  const [bx0, by0, bx1, by1] = r.band;
  const box: Pt[] = [[bx0, by0], [bx1, by0], [bx1, by1], [bx0, by1]];
  const hb = Math.min(ph, ((by1 - by0) * pw) / (bx1 - bx0));
  const my = Math.min(py + ph - hb / 2, Math.max(py + hb / 2, y(px + pw / 2)));
  const wide: Pt[] = [[px, my - hb / 2], [px + pw, my - hb / 2], [px + pw, my + hb / 2], [px, my + hb / 2]];
  const slid = open.map((p, i): Pt => {
    const q = w(p);
    return [lerp(q[0], slot[i][0], slide), lerp(q[1], slot[i][1], slide)];
  });
  const bandPts = slid.map((at, i) => toWorld([lerp(at[0], box[i][0], spread), lerp(at[1], box[i][1], spread)], z));
  const bandUv = open.map((p, i) => {
    const u0 = uvOf(p), u1 = uvOf(strip[i]), u2 = uvOf(wide[i]);
    const at: Pt = [lerp(u0[0], u1[0], slide), lerp(u0[1], u1[1], slide)];
    return [lerp(at[0], u2[0], spread), lerp(at[1], u2[1], spread)] as Pt;
  });
  setQuad(parts.band, bandPts, bandUv, m.full ? [[0, 0.5], [1, 0.5], [1, 0.5], [0, 0.5]] : FLAT);
  // with no picture on the card the photograph first shows as the slit slides into its row
  parts.band.mesh.visible = shown || slide > 0;
  // in its row the band carries no more light than the year's other rows
  (parts.band.mesh.material as THREE.MeshBasicMaterial).color.setScalar(lerp(1, m.gain, spread));
  // the accent line the dot drew stays on the photograph from the moment it is finished: on the near layer's cut while
  // the photograph is open, then along the slit's middle it folds, levels and slides with the slit, so it arrives in
  // the row the row's length, and settles into the dark under the band as the slit spreads into it
  const thick = lerp(12 * s, lerp(6, 4, spread), slide) / 2;
  const foot = lerp(r.y, r.rule, spread);
  const [mid0, mid1] = ([[x0, y(x0)], [x1, y(x1)]] as Pt[]).map((p, i): Pt => {
    const q = near(p);
    return [lerp(q[0], i ? r.x1 : r.x0, slide), lerp(q[1], foot, slide)];
  });
  const nx = -(mid1[1] - mid0[1]), ny = mid1[0] - mid0[0];
  const k = thick / Math.max(1e-6, Math.hypot(nx, ny));
  const zr = lerp(layer.z, restZ(index), slide) + lerp(2 * s, 0.62, slide);
  setQuad(parts.rule, [toWorld([mid0[0] - nx * k, mid0[1] - ny * k], zr), toWorld([mid1[0] - nx * k, mid1[1] - ny * k], zr),
    toWorld([mid1[0] + nx * k, mid1[1] + ny * k], zr), toWorld([mid0[0] + nx * k, mid0[1] + ny * k], zr)], [[0, 1], [1, 1], [1, 0], [0, 0]]);
  parts.rule.mesh.renderOrder = 100 + index * 10 + 5;
  // the line stays on the photograph only where the card asks for it; it shows again as the halves close onto it
  parts.rule.mesh.visible = plan.photo.rule || fold > 0;
  // the halves, on either side of the slit: closing, each one's outer edge comes down onto the slit while the picture
  // under it stands still, so the photograph closes onto its own line the way it opened out of it; the one above on
  // the near layer, its cut catching the light, the one below on the far one
  const above: Pt[] = [[x0, lerp(top, y(x0) - bh, fold)], [x1, lerp(top, y(x1) - bh, fold)], [x1, y(x1) - bh], [x0, y(x0) - bh]];
  const below: Pt[] = [[x0, y(x0) + bh], [x1, y(x1) + bh], [x1, lerp(bottom, y(x1) + bh, fold)], [x0, lerp(bottom, y(x0) + bh, fold)]];
  setQuad(parts.above, above.map((p) => toWorld(near(p), layer.z)), above.map(uvOf), m.full ? WHOLE : FLAT);
  setQuad(parts.below, below.map((p) => toWorld(w(p), lift)), below.map(uvOf), m.full ? [[0, 0.5], [1, 0.5], [1, 1], [0, 1]] : FLAT);
  // the near layer's shadow on the far one: from its cut, falling right and down as far as it stands off, soft
  const fall: Pt = [0.35 * layer.sep, 0.58 * layer.sep];
  const soft = 18 + 0.25 * layer.sep;
  const cutTop = [near([x0, y(x0) - bh]), near([x1, y(x1) - bh])];
  const cutPts: Pt[] = [[cutTop[0][0] - soft, cutTop[0][1] - soft], [cutTop[1][0] + fall[0] + soft, cutTop[1][1] - soft],
    [cutTop[1][0] + fall[0] + soft, cutTop[1][1] + fall[1] + soft], [cutTop[0][0] - soft, cutTop[0][1] + fall[1] + soft]];
  setQuad(parts.cut, cutPts.map((p) => toWorld(p, lift + 0.5)), WHOLE);
  setBox(parts.cut.mesh.material as THREE.Material, cutPts[1][0] - cutPts[0][0], fall[1] + 2 * soft, 0, soft);
  (parts.cut.mesh.material as THREE.MeshBasicMaterial).opacity = CUT_DARK * layer.on;
  parts.cut.mesh.visible = layer.on > 0.01 && shown && m.full;
  // the halves are the photograph from the open on, whole and at its own exposure, until they have closed onto the slit
  const seen = shown && t >= a.open[0] && fold < 1;
  for (const key of ['above', 'below'] as const) {
    parts[key].mesh.castShadow = seen;
    parts[key].mesh.visible = seen;
  }
  parts.band.mesh.castShadow = z > 3;
  // the far layer is drawn before the near one
  const order = 100 + index * 10;
  parts.band.mesh.renderOrder = order;
  parts.below.mesh.renderOrder = order + 1;
  parts.cut.mesh.renderOrder = order + 2;
  parts.above.mesh.renderOrder = order + 3;
  return (
    <group>
      <primitive object={parts.field.mesh} />
      <primitive object={parts.drop.mesh} />
      <primitive object={parts.card.mesh} />
      <primitive object={parts.band.mesh} />
      <primitive object={parts.below.mesh} />
      <primitive object={parts.cut.mesh} />
      <primitive object={parts.above.mesh} />
      <primitive object={parts.rule.mesh} />
    </group>
  );
};
