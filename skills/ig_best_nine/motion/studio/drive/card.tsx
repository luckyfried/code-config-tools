// A photograph's card on the wall: the picture flies in as a tile, the blade crosses its edge and the part above the
// edge peels toward the camera, uncovering the field; when the camera leaves, the field hinges away and the picture
// trims down into its slice of the closer's wall, where it stays.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span, type Pt} from '../../system/three/motion';
import {onWall, type Card, type Plan} from './plan';

export const cardScale = (c: Card) => c.T.s;
/** How far a card stands off the wall while it is the one the camera is on. */
export const liftOf = (c: Card) => 90 * c.T.s;
/** Where a card rests once it is in its slice: a hair over the cards before it. */
export const restZ = (index: number) => 0.03 * (index + 1);
const MARGIN = 0.12;

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

/** The card's timings in beats. */
export const timesOf = (c: Card) => ({
  fly: c.hook ? [0, 0.3] : [c.arrive - 0.5, 0.75],
  peel: [c.cut + 0.05, 0.5],
  leave: [c.leave - 0.6, 0.75],
});

/** How a card stands off its landing while it flies in, `rest` running from 1 (furthest) to 0 (landed), and how much
 * of the lens distance it starts from. The hook falls flat from the lens. Every other card takes its own line, in
 * three ways that turn through the film so no two cards in a row arrive alike: hinged flat about its edge (tipping
 * the way its edge climbs), sliding in along its edge from the end the dot waits at, or rising square to its edge from
 * below it. */
const entryOf = (c: Card, index: number, axis: THREE.Vector3, rest: number, w: number, h: number) => {
  const m = new THREE.Matrix4();
  if (c.hook) return {turn: m.makeRotationFromEuler(new THREE.Euler(rest * -0.5, rest * -0.45, rest * 0.12)), near: 0.82};
  const up = new THREE.Vector3(-axis.y, axis.x, 0);
  const tilt = (about: THREE.Vector3, angle: number) => new THREE.Matrix4().makeRotationAxis(about, angle);
  if (index % 3 === 1) return {turn: tilt(axis, rest * (c.line[1] < c.line[0] ? 1.45 : -1.45)), near: 0.7};
  if (index % 3 === 2) {
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

export type CardProps = {plan: Plan; card: Card; index: number; t: number; texture: THREE.Texture};

export const CardView: React.FC<CardProps> = ({plan, card: c, index, t, texture}) => {
  const {W, H} = plan;
  const parts = useMemo(() => {
    const photo = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, side: THREE.DoubleSide});
    const above = new THREE.MeshBasicMaterial({map: texture, toneMapped: false, transparent: true, side: THREE.DoubleSide});
    const field = new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, side: THREE.DoubleSide});
    const shade = new THREE.MeshBasicMaterial({map: ramp(), color: '#000000', toneMapped: false, transparent: true, depthWrite: false});
    const gleam = new THREE.MeshBasicMaterial({color: new THREE.Color(1, 0.86, 0.62).multiplyScalar(4), toneMapped: false, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending});
    return {below: quad(photo), above: quad(above), field: quad(field), shade: quad(shade), gleam: quad(gleam), mats: {photo, above, field, shade, gleam}};
  }, [texture]);
  const tm = timesOf(c);
  const fly = span(t, tm.fly[0], tm.fly[1], bezier([0.12, 0.8, 0.25, 1]));
  if (t < tm.fly[0] - 0.01) return null;
  const s = c.T.s;
  const lift = liftOf(c);
  const settled = restZ(index);
  const leave = span(t, tm.leave[0], tm.leave[1], bezier(plan.ease.move));
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
  const {turn, near} = entryOf(c, index, axis, 1 - fly, W * s, H * s);
  const zFly = (1 - fly) * D * near;
  const pivot = c.hook ? toWorld(w([W / 2, H / 2]), 0) : e0.clone().lerp(e1, 0.5);
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
  setQuad(parts.below, belowPts.map((p) => flown(toWorld(p, z))), belowPts.map(uvWall));
  const hinge = (pts: Pt[], zz: number, angle: number, rise: number) => {
    const m = new THREE.Matrix4().makeRotationAxis(axis, angle);
    const o = e0.clone().setZ(zz);
    return pts.map((p) => flown(toWorld(w(p), zz).sub(o).applyMatrix4(m).add(o).add(new THREE.Vector3(0, rise, rise * 0.6))));
  };
  // the picture above the edge: whole until the blade, then peeled toward the lens
  const peelAngle = peel * 1.9;
  setQuad(parts.above, hinge(q.above, lift + 10 * s, peelAngle, peel * peel * 260 * s), q.above.map(uvOf));
  parts.mats.above.opacity = 1 - span(t, c.cut + 0.3, 0.3);
  // the field: there from the blade on, hinged away as the camera leaves
  const fieldOn = span(t, c.cut, 0.06);
  const fieldAngle = leave * 1.75;
  setQuad(parts.field, hinge(q.field, lift + 6 * s, fieldAngle, leave * leave * 200 * s), q.field.map(() => [0, 0] as Pt));
  parts.mats.field.color.set(plan.colors[c.field] ?? c.field);
  parts.mats.field.opacity = fieldOn * (1 - span(leave, 0.35, 0.5));
  // the field's edge throws a soft shadow down onto the picture
  const band = 46 * s;
  const shadePts: Pt[] = [[q.field[3][0], q.field[3][1]], [q.field[2][0], q.field[2][1]], [q.field[2][0], q.field[2][1] + band / s], [q.field[3][0], q.field[3][1] + band / s]];
  setQuad(parts.shade, shadePts.map((p) => flown(toWorld(w(p), lift + 1.5 * s))), [[0, 1], [1, 1], [1, 0], [0, 0]]);
  parts.mats.shade.opacity = 0.32 * fieldOn * (1 - leave);
  // the blade's gleam along the edge, bright as it crosses and dying after
  const g = span(t, c.cut, 0.12) * (1 - span(t, c.cut + 0.2, 0.5));
  const thick = 2.2 * s;
  const along = span(t, c.cut, 0.25, bezier([0.3, 0, 0.2, 1]));
  const gl: Pt[] = [[0, c.line[0] - thick], [W * along, edgeY(c, W, W * along) - thick], [W * along, edgeY(c, W, W * along) + thick], [0, c.line[0] + thick]];
  setQuad(parts.gleam, gl.map((p) => flown(toWorld(w(p), lift + 12 * s))), [[0, 0], [1, 0], [1, 1], [0, 1]]);
  parts.mats.gleam.opacity = g;
  const casting = z > 3 || zFly > 3;
  parts.below.mesh.castShadow = casting;
  parts.above.mesh.castShadow = parts.mats.above.opacity > 0.5;
  parts.field.mesh.castShadow = casting && parts.mats.field.opacity > 0.5;
  const order = index * 10;
  parts.below.mesh.renderOrder = order;
  parts.shade.mesh.renderOrder = order + 1;
  parts.field.mesh.renderOrder = order + 2;
  parts.above.mesh.renderOrder = order + 3;
  parts.gleam.mesh.renderOrder = order + 4;
  return (
    <group>
      <primitive object={parts.below.mesh} />
      {parts.mats.shade.opacity > 0.002 ? <primitive object={parts.shade.mesh} /> : null}
      {parts.mats.field.opacity > 0.002 ? <primitive object={parts.field.mesh} /> : null}
      {parts.mats.above.opacity > 0.002 ? <primitive object={parts.above.mesh} /> : null}
      {g > 0.002 ? <primitive object={parts.gleam.mesh} /> : null}
    </group>
  );
};
