// Geometry builders and a merging kit: every static piece of the town is added with a vertex color and a transform,
// then merged into one mesh per material, so the whole street draws in a handful of calls.
import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _e = new THREE.Euler();
const _s = new THREE.Vector3();
const _p = new THREE.Vector3();

/** A transform from position, rotation (radians, XYZ), and scale. */
export function xf(x = 0, y = 0, z = 0, rx = 0, ry = 0, rz = 0, sx = 1, sy = 1, sz = 1) {
  _e.set(rx, ry, rz);
  _q.setFromEuler(_e);
  _s.set(sx, sy, sz);
  _p.set(x, y, z);
  return new THREE.Matrix4().compose(_p, _q, _s);
}

/** A box whose UVs run one unit per meter on every face, so plank and grain textures keep their scale. */
export function box(w, h, d) {
  const g = new THREE.BoxGeometry(w, h, d);
  const uv = g.attributes.uv;
  // Faces in order: +x, -x, +y, -y, +z, -z; four vertices each.
  const spans = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
  for (let face = 0; face < 6; face += 1) {
    const [su, sv] = spans[face];
    for (let k = 0; k < 4; k += 1) {
      const i = face * 4 + k;
      uv.setXY(i, uv.getX(i) * su, uv.getY(i) * sv);
    }
  }
  return g;
}

/** A cylinder with UVs scaled to meters around and along it. */
export function cylinder(rTop, rBottom, h, radial = 10, open = false) {
  const g = new THREE.CylinderGeometry(rTop, rBottom, h, radial, 1, open);
  const uv = g.attributes.uv;
  const around = Math.PI * (rTop + rBottom);
  for (let i = 0; i < uv.count; i += 1) uv.setXY(i, uv.getX(i) * around, uv.getY(i) * h);
  return g;
}

export class Kit {
  constructor() {
    this.buckets = new Map();
  }

  /** Adds geometry to the bucket `key`, painted `color`, placed by `matrix`. */
  add(key, geometry, color, matrix) {
    let g = geometry.index ? geometry.toNonIndexed() : geometry.clone();
    if (matrix) g.applyMatrix4(matrix);
    const count = g.attributes.position.count;
    if (!g.attributes.normal) g.computeVertexNormals();
    if (!g.attributes.uv) g.setAttribute("uv", new THREE.Float32BufferAttribute(new Float32Array(count * 2), 2));
    for (const name of Object.keys(g.attributes)) {
      if (!["position", "normal", "uv"].includes(name)) g.deleteAttribute(name);
    }
    const c = color instanceof THREE.Color ? color : new THREE.Color(color);
    const colors = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      colors[i * 3] = c.r;
      colors[i * 3 + 1] = c.g;
      colors[i * 3 + 2] = c.b;
    }
    g.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    g.morphAttributes = {};
    if (!this.buckets.has(key)) this.buckets.set(key, []);
    this.buckets.get(key).push(g);
    return g;
  }

  /** One mesh per bucket, with the material `materials[key]`. */
  build(materials, { castShadow = true, receiveShadow = true } = {}) {
    const group = new THREE.Group();
    for (const [key, list] of this.buckets) {
      const merged = mergeGeometries(list, false);
      list.forEach((g) => g.dispose());
      merged.computeBoundingSphere();
      const mesh = new THREE.Mesh(merged, materials[key]);
      mesh.name = key;
      mesh.castShadow = castShadow && key !== "glass" && key !== "glow";
      mesh.receiveShadow = receiveShadow;
      mesh.matrixAutoUpdate = false;
      mesh.updateMatrix();
      group.add(mesh);
    }
    this.buckets.clear();
    return group;
  }
}

/** A small seeded random, so the town is the same town on every load. */
export function seeded(seed = 1) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export { _m as scratchMatrix };
