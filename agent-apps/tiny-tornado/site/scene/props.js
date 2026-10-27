// The town's props, each built from primitives into one geometry. Every part names a palette slot (tokens.js PALETTE)
// so a theme recolors it, and every vertex carries a flex value: how far the wind may bend it (0 for a cow, rising
// up a tree's trunk to its crown). Swap a prop by replacing its function; the dimensions are in meters.
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { PAL } from "./tokens.js";

const m4 = new THREE.Matrix4();
const q = new THREE.Quaternion();
const e = new THREE.Euler();
const v = new THREE.Vector3();
const s = new THREE.Vector3();

function part(geometry, pal, { x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1 } = {}) {
  const g = geometry.index ? geometry.toNonIndexed() : geometry;
  g.deleteAttribute("uv");
  m4.compose(v.set(x, y, z), q.setFromEuler(e.set(rx, ry, rz)), s.set(sx, sy, sz));
  g.applyMatrix4(m4);
  const count = g.getAttribute("position").count;
  g.setAttribute("aPal", new THREE.BufferAttribute(new Float32Array(count).fill(pal), 1));
  return g;
}

function finish(parts, flex) {
  const g = mergeGeometries(parts, false);
  const pos = g.getAttribute("position");
  const f = new Float32Array(pos.count);
  for (let i = 0; i < pos.count; i++) f[i] = flex(pos.getX(i), pos.getY(i), pos.getZ(i));
  g.setAttribute("aFlex", new THREE.BufferAttribute(f, 1));
  g.computeBoundingSphere();
  return g;
}

const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
const cyl = (rt, rb, h, seg = 10) => new THREE.CylinderGeometry(rt, rb, h, seg);
const rigid = () => 0;

export function fence() {
  return finish([
    part(box(0.14, 1.0, 0.14), PAL.wood, { x: -1, y: 0.5 }),
    part(box(0.14, 1.0, 0.14), PAL.wood, { x: 1, y: 0.5 }),
    part(box(2.08, 0.11, 0.06), PAL.trim, { y: 0.45, z: 0.07 }),
    part(box(2.08, 0.11, 0.06), PAL.trim, { y: 0.82, z: 0.07 }),
  ], (x, y) => 0.18 * y + (Math.abs(x) < 0.95 ? 0.32 * y : 0));
}

export function hay() {
  return finish([
    part(cyl(0.6, 0.6, 1.1, 14), PAL.hay, { y: 0.6, rz: Math.PI / 2 }),
    part(cyl(0.42, 0.42, 1.14, 14), PAL.wood, { y: 0.6, rz: Math.PI / 2, sx: 1, sy: 1, sz: 1 }),
  ], rigid);
}

export function treeRound() {
  return finish([
    part(cyl(0.16, 0.24, 1.9, 7), PAL.wood, { y: 0.95 }),
    part(new THREE.IcosahedronGeometry(1.35, 0), PAL.leaf, { y: 2.6 }),
    part(new THREE.IcosahedronGeometry(0.95, 0), PAL.leaf, { x: 0.55, y: 3.35, z: -0.2, ry: 0.6 }),
    part(new THREE.IcosahedronGeometry(0.8, 0), PAL.pine, { x: -0.6, y: 2.2, z: 0.45, ry: 1.2 }),
  ], (x, y) => Math.pow(Math.max(y, 0) / 4.2, 1.6));
}

export function treePine() {
  return finish([
    part(cyl(0.14, 0.2, 1.3, 6), PAL.wood, { y: 0.65 }),
    part(cyl(0, 1.45, 2.0, 8), PAL.pine, { y: 2.0 }),
    part(cyl(0, 1.1, 1.8, 8), PAL.pine, { y: 3.0, ry: 0.3 }),
    part(cyl(0, 0.75, 1.5, 8), PAL.pine, { y: 3.95, ry: 0.6 }),
  ], (x, y) => Math.pow(Math.max(y, 0) / 4.7, 1.6));
}

export function cow() {
  return finish([
    part(box(1.5, 0.72, 0.72), PAL.cow, { y: 0.98 }),
    part(box(0.5, 0.5, 0.75), PAL.spot, { x: 0.18, y: 1.06 }),
    part(box(0.36, 0.42, 0.75), PAL.spot, { x: -0.45, y: 0.92 }),
    part(box(0.3, 0.12, 0.6), PAL.spot, { x: -0.1, y: 1.35 }),
    part(box(0.46, 0.44, 0.44), PAL.cow, { x: 0.94, y: 1.22 }),
    part(box(0.2, 0.24, 0.36), PAL.spot, { x: 1.2, y: 1.12 }),
    part(box(0.06, 0.16, 0.06), PAL.trim, { x: 0.94, y: 1.5, z: 0.16, rz: -0.3 }),
    part(box(0.06, 0.16, 0.06), PAL.trim, { x: 0.94, y: 1.5, z: -0.16, rz: -0.3 }),
    part(box(0.08, 0.14, 0.2), PAL.spot, { x: 0.9, y: 1.34, z: 0.27 }),
    part(box(0.08, 0.14, 0.2), PAL.spot, { x: 0.9, y: 1.34, z: -0.27 }),
    part(box(0.17, 0.66, 0.17), PAL.cow, { x: 0.55, y: 0.33, z: 0.22 }),
    part(box(0.17, 0.66, 0.17), PAL.cow, { x: 0.55, y: 0.33, z: -0.22 }),
    part(box(0.17, 0.66, 0.17), PAL.cow, { x: -0.55, y: 0.33, z: 0.22 }),
    part(box(0.17, 0.66, 0.17), PAL.cow, { x: -0.55, y: 0.33, z: -0.22 }),
    part(box(0.18, 0.08, 0.18), PAL.spot, { x: 0.55, y: 0.04, z: 0.22 }),
    part(box(0.18, 0.08, 0.18), PAL.spot, { x: -0.55, y: 0.04, z: -0.22 }),
    part(box(0.06, 0.6, 0.06), PAL.cow, { x: -0.78, y: 0.85, rz: -0.25 }),
    part(box(0.2, 0.16, 0.26), PAL.trim, { x: -0.2, y: 0.58 }),
  ], rigid);
}

export function car() {
  return finish([
    part(box(2.5, 0.55, 1.2), PAL.carA, { y: 0.6 }),
    part(box(1.35, 0.52, 1.1), PAL.window, { x: -0.12, y: 1.12 }),
    part(box(1.25, 0.1, 1.14), PAL.carA, { x: -0.12, y: 1.42 }),
    part(box(0.12, 0.5, 1.12), PAL.carA, { x: 0.5, y: 1.12 }),
    part(box(0.1, 0.18, 0.32), PAL.trim, { x: 1.26, y: 0.66, z: 0.38 }),
    part(box(0.1, 0.18, 0.32), PAL.trim, { x: 1.26, y: 0.66, z: -0.38 }),
    part(box(2.56, 0.12, 1.24), PAL.tire, { y: 0.36 }),
    ...[[0.8, 0.6], [0.8, -0.6], [-0.8, 0.6], [-0.8, -0.6]].map(([x, z]) =>
      part(cyl(0.32, 0.32, 0.24, 12), PAL.tire, { x, y: 0.32, z, rx: Math.PI / 2 })),
  ], rigid);
}

export function truck() {
  return finish([
    part(box(2.9, 0.6, 1.3), PAL.carB, { y: 0.7 }),
    part(box(1.05, 0.62, 1.22), PAL.carB, { x: 0.65, y: 1.3 }),
    part(box(0.9, 0.42, 1.24), PAL.window, { x: 0.68, y: 1.36 }),
    part(box(1.4, 0.3, 0.08), PAL.carB, { x: -0.75, y: 1.12, z: 0.61 }),
    part(box(1.4, 0.3, 0.08), PAL.carB, { x: -0.75, y: 1.12, z: -0.61 }),
    part(box(0.08, 0.3, 1.3), PAL.carB, { x: -1.42, y: 1.12 }),
    part(box(0.1, 0.18, 0.34), PAL.trim, { x: 1.46, y: 0.78, z: 0.4 }),
    part(box(0.1, 0.18, 0.34), PAL.trim, { x: 1.46, y: 0.78, z: -0.4 }),
    part(box(2.96, 0.14, 1.34), PAL.tire, { y: 0.4 }),
    ...[[0.9, 0.66], [0.9, -0.66], [-0.9, 0.66], [-0.9, -0.66]].map(([x, z]) =>
      part(cyl(0.36, 0.36, 0.26, 12), PAL.tire, { x, y: 0.36, z, rx: Math.PI / 2 })),
  ], rigid);
}

function prism(points, depth) {
  const shape = new THREE.Shape(points.map(([x, y]) => new THREE.Vector2(x, y)));
  const g = new THREE.ExtrudeGeometry(shape, { depth, bevelEnabled: false });
  g.translate(0, 0, -depth / 2);
  return g;
}

export function barn() {
  const W = 6.2;
  const L = 8.4;
  const H = 4.3;
  const parts = [
    part(box(W, H, L), PAL.barn, { y: H / 2 }),
    part(prism([[-3.3, H], [3.3, H], [2.5, H + 1.8], [0, H + 2.9], [-2.5, H + 1.8]], L + 0.5), PAL.roof),
    part(prism([[-3.1, H - 0.02], [3.1, H - 0.02], [2.35, H + 1.7], [0, H + 2.75], [-2.35, H + 1.7]], L + 0.04), PAL.barn),
    part(box(2.8, 3.0, 0.12), PAL.barn, { y: 1.5, z: L / 2 + 0.06 }),
    part(box(3.0, 0.18, 0.16), PAL.trim, { y: 3.05, z: L / 2 + 0.1 }),
    part(box(0.18, 3.0, 0.16), PAL.trim, { x: -1.45, y: 1.5, z: L / 2 + 0.1 }),
    part(box(0.18, 3.0, 0.16), PAL.trim, { x: 1.45, y: 1.5, z: L / 2 + 0.1 }),
    part(box(0.16, 3.9, 0.14), PAL.trim, { y: 1.5, z: L / 2 + 0.12, rz: Math.atan2(2.8, 3.0) }),
    part(box(0.16, 3.9, 0.14), PAL.trim, { y: 1.5, z: L / 2 + 0.12, rz: -Math.atan2(2.8, 3.0) }),
    part(box(1.3, 1.1, 0.12), PAL.window, { y: H + 0.9, z: L / 2 + 0.05 }),
    part(box(1.5, 0.14, 0.16), PAL.trim, { y: H + 1.5, z: L / 2 + 0.08 }),
    part(box(1.5, 0.14, 0.16), PAL.trim, { y: H + 0.3, z: L / 2 + 0.08 }),
    part(box(W + 0.1, 0.16, 0.16), PAL.trim, { y: 0.08, z: L / 2 + 0.02 }),
    part(box(W + 0.1, 0.16, 0.16), PAL.trim, { y: H, z: L / 2 + 0.02 }),
  ];
  for (const z of [-2.4, 0, 2.4]) {
    parts.push(part(box(0.1, 0.8, 1.0), PAL.window, { x: W / 2 + 0.03, y: 2.6, z }));
    parts.push(part(box(0.1, 0.8, 1.0), PAL.window, { x: -W / 2 - 0.03, y: 2.6, z }));
  }
  parts.push(part(box(0.5, 0.5, 0.9), PAL.trim, { y: H + 3.05 }));
  parts.push(part(prism([[-0.4, 0], [0.4, 0], [0, 0.35]], 1.0), PAL.roof, { y: H + 3.28 }));
  return finish(parts, rigid);
}

export function silo() {
  return finish([
    part(cyl(1.45, 1.45, 7.5, 18), PAL.metal, { y: 3.75 }),
    part(new THREE.SphereGeometry(1.45, 18, 8, 0, Math.PI * 2, 0, Math.PI / 2), PAL.metal, { y: 7.5 }),
    part(cyl(1.5, 1.5, 0.16, 18), PAL.trim, { y: 2.2 }),
    part(cyl(1.5, 1.5, 0.16, 18), PAL.trim, { y: 4.6 }),
    part(cyl(1.5, 1.5, 0.16, 18), PAL.trim, { y: 7.0 }),
    part(box(0.3, 6.8, 0.3), PAL.roof, { x: 1.5, y: 3.6 }),
  ], rigid);
}

function houseWith(wall) {
  const W = 4.6;
  const L = 4.2;
  const H = 3.0;
  return finish([
    part(box(W, H, L), wall, { y: H / 2 }),
    part(prism([[-2.75, H - 0.05], [2.75, H - 0.05], [0, H + 1.9]], L + 0.5), PAL.roof),
    part(box(0.9, 1.8, 0.1), PAL.wood, { x: -0.9, y: 0.9, z: L / 2 + 0.04 }),
    part(box(1.0, 0.9, 0.08), PAL.window, { x: 1.0, y: 1.6, z: L / 2 + 0.04 }),
    part(box(1.15, 0.12, 0.1), PAL.trim, { x: 1.0, y: 1.1, z: L / 2 + 0.06 }),
    part(box(0.08, 0.9, 0.9), PAL.window, { x: W / 2 + 0.03, y: 1.6, z: 0.6 }),
    part(box(0.08, 0.9, 0.9), PAL.window, { x: -W / 2 - 0.03, y: 1.6, z: -0.6 }),
    part(box(1.0, 0.9, 0.08), PAL.window, { x: -0.6, y: 1.6, z: -L / 2 - 0.04 }),
    part(box(0.6, 1.4, 0.6), PAL.roof, { x: 1.3, y: H + 1.4, z: -0.6 }),
    part(box(1.8, 0.14, 1.0), PAL.trim, { x: -0.9, y: 0.07, z: L / 2 + 0.5 }),
  ], rigid);
}
export const house = () => houseWith(PAL.house);
export const houseB = () => houseWith(PAL.houseB);

// A plank: the barn and the houses come apart into these.
export function plank() {
  return finish([part(box(1.5, 0.12, 0.42), PAL.barn)], rigid);
}
