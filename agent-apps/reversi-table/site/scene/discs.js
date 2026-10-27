// The discs: each one two lathed halves, the light face's half and the dark face's half, drawn as one InstancedMesh
// per face color that share every instance's matrix. A disc's turn is a rotation of that matrix.
import { InstancedMesh, LatheGeometry, Vector2, Vector3, Quaternion, Matrix4, Color, DynamicDrawUsage } from "three";
import { BLACK } from "../game/reversi.js";

export const DISC_R = 0.42;
export const DISC_H = 0.075; // half the thickness
export const DISC_TOP = DISC_H * 2 + 0.03; // the dome's peak above the board
const BEVEL = 0.036;
const DOME = DISC_TOP - DISC_H * 2; // the faces rise toward the center, so the lacquer carries the key light's highlight

function halfProfile(sign) {
  // Points run from the bottom of the profile to the top, so the lathe's normals face out.
  const pts = [];
  const arc = [];
  for (let k = 0; k <= 8; k += 1) {
    const a = (k / 8) * (Math.PI / 2);
    arc.push(new Vector2(DISC_R - BEVEL + BEVEL * Math.cos(a), DISC_H - BEVEL + BEVEL * Math.sin(a)));
  }
  const dome = [];
  for (let k = 1; k <= 6; k += 1) {
    const x = (DISC_R - BEVEL) * (1 - k / 6);
    const t = x / (DISC_R - BEVEL);
    dome.push(new Vector2(Math.max(0.0001, x), DISC_H + DOME * (1 - t * t)));
  }
  if (sign > 0) {
    pts.push(new Vector2(DISC_R, 0));
    for (const p of arc) pts.push(p);
    for (const p of dome) pts.push(p);
  } else {
    for (let k = dome.length - 1; k >= 0; k -= 1) pts.push(new Vector2(dome[k].x, -dome[k].y));
    for (let k = arc.length - 1; k >= 0; k -= 1) pts.push(new Vector2(arc[k].x, -arc[k].y));
    pts.push(new Vector2(DISC_R, 0));
  }
  return pts;
}

// The lathe leaves the center of each face with a slanted normal; the dome's peak faces straight out.
function settlePole(geometry, up) {
  const position = geometry.attributes.position;
  const normal = geometry.attributes.normal;
  for (let i = 0; i < position.count; i += 1) {
    if (Math.hypot(position.getX(i), position.getZ(i)) < 0.001) normal.setXYZ(i, 0, up, 0);
  }
  normal.needsUpdate = true;
  return geometry;
}

export function discGeometries(segments) {
  return {
    light: settlePole(new LatheGeometry(halfProfile(1), segments), 1),
    dark: settlePole(new LatheGeometry(halfProfile(-1), segments), -1),
  };
}

const FLIP_BASE = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), Math.PI);
const IDENTITY = new Quaternion();
const turn = new Quaternion();
const q = new Quaternion();
const axis = new Vector3();
const pos = new Vector3();
const scl = new Vector3();
const m = new Matrix4();
const ZERO = new Matrix4().makeScale(0, 0, 0);

/** The orientation of a disc resting on `show`'s face, turned `angle` about (ax, 0, az). */
export function discQuaternion(show, angle, ax, az, out) {
  out.copy(show === BLACK ? FLIP_BASE : IDENTITY);
  if (angle !== 0) {
    axis.set(ax, 0, az).normalize();
    turn.setFromAxisAngle(axis, angle);
    out.premultiply(turn);
  }
  return out;
}

export class DiscPool {
  constructor(geometries, lightMaterial, darkMaterial, capacity) {
    this.light = new InstancedMesh(geometries.light, lightMaterial, capacity);
    this.dark = new InstancedMesh(geometries.dark, darkMaterial, capacity);
    for (const mesh of [this.light, this.dark]) {
      mesh.instanceMatrix.setUsage(DynamicDrawUsage);
      mesh.castShadow = true;
      mesh.receiveShadow = false;
      mesh.frustumCulled = false;
      for (let i = 0; i < capacity; i += 1) mesh.setMatrixAt(i, ZERO);
    }
    this.capacity = capacity;
  }

  set(i, x, y, z, quaternion, scale) {
    pos.set(x, y, z);
    scl.setScalar(scale);
    m.compose(pos, quaternion, scl);
    this.light.setMatrixAt(i, m);
    this.dark.setMatrixAt(i, m);
  }

  hide(i) {
    this.light.setMatrixAt(i, ZERO);
    this.dark.setMatrixAt(i, ZERO);
  }

  commit() {
    this.light.instanceMatrix.needsUpdate = true;
    this.dark.instanceMatrix.needsUpdate = true;
  }

  addTo(parent) {
    parent.add(this.light, this.dark);
  }
}

export function applyDiscTokens(lightMaterial, darkMaterial, tokens) {
  lightMaterial.color = new Color(tokens.discLight);
  darkMaterial.color = new Color(tokens.discDark);
  lightMaterial.sheenColor = new Color(tokens.discSheen).multiplyScalar(0.5);
  darkMaterial.sheenColor = new Color(tokens.discSheen).multiplyScalar(0.14);
  // A day room's studio light pushes the light face toward white; set it a step down there so its glint still shows.
  if (lightMaterial.glintBase) lightMaterial.glintBase.value = 1 - 0.28 * Math.min(1, Math.max(0, (tokens.env - 0.5) / 0.5));
}

export { q as scratchQuaternion };
