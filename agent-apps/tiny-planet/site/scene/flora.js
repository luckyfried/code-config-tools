// Trees, pines, rocks, and grass tufts. Each kind is one function that returns a colored geometry standing on its
// root at the origin with +Y up; swapping a tree is replacing `tree()`. Instances are placed by MeshSurfaceSampler
// with per-face weights from the planet, oriented outward, and bucketed by direction so far chunks are culled.
import * as THREE from "three";
import { MeshSurfaceSampler } from "three/addons/math/MeshSurfaceSampler.js";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { floraMaterial, stoneMaterial } from "./materials.js";

function painted(geometry, color, shadeTop = 1, shadeBottom = 1) {
  const g = geometry.index ? geometry.toNonIndexed() : geometry;
  const p = g.attributes.position;
  g.computeBoundingBox();
  const { min, max } = g.boundingBox;
  const colors = new Float32Array(p.count * 3);
  const c = new THREE.Color();
  for (let i = 0; i < p.count; i++) {
    const t = (p.getY(i) - min.y) / Math.max(1e-6, max.y - min.y);
    c.copy(color).multiplyScalar(THREE.MathUtils.lerp(shadeBottom, shadeTop, t));
    colors.set([c.r, c.g, c.b], i * 3);
  }
  g.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  g.deleteAttribute("uv");
  g.computeVertexNormals();
  return g;
}

function faceted(geometry, amount, seed) {
  const p = geometry.attributes.position;
  let s = seed;
  const rand = () => {
    s = (s * 16807) % 2147483647;
    return s / 2147483647 - 0.5;
  };
  const seen = new Map();
  for (let i = 0; i < p.count; i++) {
    const key = `${p.getX(i).toFixed(3)},${p.getY(i).toFixed(3)},${p.getZ(i).toFixed(3)}`;
    let d = seen.get(key);
    if (!d) {
      d = [rand() * amount, rand() * amount, rand() * amount];
      seen.set(key, d);
    }
    p.setXYZ(i, p.getX(i) + d[0], p.getY(i) + d[1], p.getZ(i) + d[2]);
  }
  return geometry;
}

// A cone of side triangles from the apex down to a ring, with the bottom cap only when it can be seen. Built
// directly so no triangle collapses to a point: every vertex the planet's flora draws is one that shows.
function cone(radius, height, segments, cap) {
  const v = [];
  for (let i = 0; i < segments; i++) {
    const a0 = (i / segments) * Math.PI * 2;
    const a1 = ((i + 1) / segments) * Math.PI * 2;
    const x0 = Math.sin(a0) * radius;
    const z0 = Math.cos(a0) * radius;
    const x1 = Math.sin(a1) * radius;
    const z1 = Math.cos(a1) * radius;
    v.push(0, height / 2, 0, x0, -height / 2, z0, x1, -height / 2, z1);
    if (cap) v.push(0, -height / 2, 0, x1, -height / 2, z1, x0, -height / 2, z0);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
  return g;
}

// A trunk stands in the ground and ends inside its crown, so it has no caps.
const trunkOf = (top, bottom, height, segments) => new THREE.CylinderGeometry(top, bottom, height, segments, 1, true);

// A round broadleaf tree: a short trunk and two lumpy crowns.
export function tree(colors) {
  const trunk = painted(trunkOf(0.07, 0.11, 0.7, 6).translate(0, 0.35, 0), colors.worldTrunk, 1, 0.8);
  const crown = faceted(new THREE.IcosahedronGeometry(0.46, 0), 0.08, 11);
  crown.scale(1, 0.92, 1).translate(0, 0.95, 0);
  const top = faceted(new THREE.IcosahedronGeometry(0.3, 0), 0.06, 23);
  top.translate(0.08, 1.32, -0.04);
  return mergeGeometries([trunk, painted(crown, colors.worldLeaf, 1.12, 0.78), painted(top, colors.worldLeaf, 1.25, 0.95)]);
}

// A pine: a trunk and three stacked cones, darker at the skirt of each tier.
export function pine(colors) {
  const parts = [painted(trunkOf(0.05, 0.08, 0.5, 5).translate(0, 0.25, 0), colors.worldTrunk, 1, 0.8)];
  const tiers = [
    [0.5, 0.62, 0.55],
    [0.38, 0.5, 0.9],
    [0.25, 0.42, 1.22],
  ];
  for (const [r, h, y] of tiers) {
    parts.push(painted(cone(r, h, 7, true).translate(0, y, 0), colors.worldLeaf2, 1.18, 0.72));
  }
  return mergeGeometries(parts);
}

export function rock(colors) {
  const g = faceted(new THREE.DodecahedronGeometry(0.32, 0), 0.12, 37);
  g.scale(1.25, 0.72, 1).translate(0, 0.12, 0);
  return painted(g, colors.worldStone, 1.1, 0.75);
}

export function tuft(colors) {
  const blades = [];
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2;
    const b = cone(0.035, 0.32 + (i % 2) * 0.12, 3, false);
    b.translate(0, 0.16, 0).rotateZ(Math.cos(a) * 0.35).rotateX(Math.sin(a) * 0.35).translate(Math.cos(a) * 0.05, 0, Math.sin(a) * 0.05);
    blades.push(painted(b, colors.worldGrass, 1.2, 0.7));
  }
  return mergeGeometries(blades);
}

const KINDS = [
  { name: "tree", make: tree, weight: "wTree", count: 520, scale: [0.75, 1.3], sway: true, sink: 0.04 },
  { name: "pine", make: pine, weight: "wPine", count: 1150, scale: [0.7, 1.35], sway: true, sink: 0.04 },
  { name: "rock", make: rock, weight: "wRock", count: 420, scale: [0.5, 1.6], sway: false, sink: 0.08 },
  { name: "tuft", make: tuft, weight: "wTuft", count: 1000, scale: [0.7, 1.3], sway: true, sink: 0.02 },
];

export function buildFlora(samplerMesh, colors, random, density) {
  const group = new THREE.Group();
  group.name = "flora";
  const buckets = new THREE.IcosahedronGeometry(1, 0);
  const bucketDirs = [];
  {
    const p = buckets.attributes.position;
    for (let i = 0; i < p.count; i += 3) {
      const c = new THREE.Vector3().fromBufferAttribute(p, i)
        .add(new THREE.Vector3().fromBufferAttribute(p, i + 1))
        .add(new THREE.Vector3().fromBufferAttribute(p, i + 2))
        .normalize();
      bucketDirs.push(c);
    }
  }
  buckets.dispose();

  const sway = floraMaterial();
  const stone = stoneMaterial();
  const meshes = [];
  const position = new THREE.Vector3();
  const normal = new THREE.Vector3();
  const up = new THREE.Vector3(0, 1, 0);
  const dir = new THREE.Vector3();
  const q = new THREE.Quaternion();
  const yaw = new THREE.Quaternion();
  const s = new THREE.Vector3();
  const m = new THREE.Matrix4();

  for (const kind of KINDS) {
    const sampler = new MeshSurfaceSampler(samplerMesh).setWeightAttribute(kind.weight).setRandomGenerator(random).build();
    const geometry = kind.make(colors);
    const perBucket = bucketDirs.map(() => []);
    for (let i = 0; i < kind.count; i++) {
      sampler.sample(position, normal);
      dir.copy(position).normalize();
      position.addScaledVector(dir, -kind.sink);
      const leanUp = dir.clone().lerp(normal, kind.name === "rock" ? 0.7 : 0.15).normalize();
      q.setFromUnitVectors(up, leanUp);
      yaw.setFromAxisAngle(up, random() * Math.PI * 2);
      q.multiply(yaw);
      const k = THREE.MathUtils.lerp(kind.scale[0], kind.scale[1], random() * random() * 0.5 + random() * 0.5);
      s.set(k, k * (0.9 + random() * 0.25), k);
      m.compose(position, q, s);
      let best = 0;
      let bestDot = -2;
      for (let b = 0; b < bucketDirs.length; b++) {
        const d = bucketDirs[b].dot(dir);
        if (d > bestDot) {
          bestDot = d;
          best = b;
        }
      }
      perBucket[best].push(m.clone());
    }
    for (const list of perBucket) {
      if (!list.length) continue;
      const mesh = new THREE.InstancedMesh(geometry, kind.sway ? sway : stone, list.length);
      list.forEach((matrix, i) => mesh.setMatrixAt(i, matrix));
      mesh.instanceMatrix.needsUpdate = true;
      mesh.computeBoundingSphere();
      mesh.castShadow = kind.name !== "tuft";
      mesh.receiveShadow = true;
      mesh.userData.full = list.length;
      meshes.push(mesh);
      group.add(mesh);
    }
  }

  function setDensity(fraction) {
    for (const mesh of meshes) mesh.count = Math.max(0, Math.round(mesh.userData.full * fraction));
  }
  setDensity(density);

  return { group, setDensity };
}
