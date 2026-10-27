// Decor: rocks that frame the tank, and every piece the shop sells (corals, a sea fan, an arch, anemones,
// driftwood, ferns, stones, grass, a hydrothermal vent, tube worms, and a bubbler), each built from code, lit by
// the caustics, and swaying where it is soft.
import * as THREE from "three";
import { patchMaterial } from "./shading.js";
import { sandHeight } from "./floor.js";
import { DEPTH_BACK } from "./world.js";

let seed = 5;
const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const reseed = (s) => { seed = s; };

function merge(list) {
  let vertices = 0;
  for (const g of list) vertices += g.attributes.position.count;
  const pos = new Float32Array(vertices * 3), nrm = new Float32Array(vertices * 3);
  const col = new Float32Array(vertices * 3), bend = new Float32Array(vertices);
  const idx = [];
  let o = 0;
  for (const g0 of list) {
    const g = g0.index ? g0 : g0;
    const n = g.attributes.position.count;
    pos.set(g.attributes.position.array, o * 3);
    nrm.set(g.attributes.normal.array, o * 3);
    if (g.attributes.color) col.set(g.attributes.color.array, o * 3);
    else col.fill(1, o * 3, (o + n) * 3);
    if (g.attributes.aBend) bend.set(g.attributes.aBend.array, o);
    if (g.index) for (const i of g.index.array) idx.push(o + i);
    else for (let i = 0; i < n; i++) idx.push(o + i);
    o += n;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
  out.setAttribute("color", new THREE.BufferAttribute(col, 3));
  out.setAttribute("aBend", new THREE.BufferAttribute(bend, 1));
  out.setIndex(idx);
  out.computeBoundingSphere();
  return out;
}

// colors a geometry from `a` at its foot to `b` at height h, and records how far up each vertex sits
function paint(geo, a, b, h, power = 1) {
  const p = geo.attributes.position;
  const col = new Float32Array(p.count * 3), bend = new Float32Array(p.count);
  const c = new THREE.Color();
  for (let i = 0; i < p.count; i++) {
    const t = THREE.MathUtils.clamp(p.getY(i) / h, 0, 1);
    c.copy(a).lerp(b, Math.pow(t, power));
    col.set([c.r, c.g, c.b], i * 3);
    bend[i] = t;
  }
  geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  geo.setAttribute("aBend", new THREE.BufferAttribute(bend, 1));
  return geo;
}

function lumpy(geo, amount, freq) {
  const p = geo.attributes.position;
  const v = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    const n = Math.sin(v.x * freq + 1.3) * Math.sin(v.y * freq * 1.3 + 0.7) * Math.sin(v.z * freq * 0.9 + 2.1);
    v.multiplyScalar(1 + n * amount);
    p.setXYZ(i, v.x, v.y, v.z);
  }
  geo.computeVertexNormals();
  return geo;
}

function rock(color, s) {
  const g = lumpy(new THREE.IcosahedronGeometry(1, 3), 0.22, 2.3 + rnd());
  g.scale(s * (0.9 + rnd() * 0.5), s * (0.55 + rnd() * 0.3), s * (0.8 + rnd() * 0.4));
  const c = color.clone().multiplyScalar(0.8 + rnd() * 0.3);
  return paint(g, c.clone().multiplyScalar(0.7), c, s * 0.8);
}

function branch(geos, from, dir, len, r, depth, a, b, maxH) {
  const g = new THREE.CylinderGeometry(r * 0.7, r, len, 7, 3);
  g.translate(0, len / 2, 0);
  const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
  g.applyQuaternion(q);
  g.translate(from.x, from.y, from.z);
  geos.push(g);
  const tip = from.clone().addScaledVector(dir.clone().normalize(), len);
  if (depth <= 0) {
    const cap = new THREE.SphereGeometry(r * 0.75, 7, 5);
    cap.translate(tip.x, tip.y, tip.z);
    geos.push(cap);
    return;
  }
  const kids = depth > 1 ? 3 : 2;
  for (let k = 0; k < kids; k++) {
    const d = dir.clone().normalize();
    d.x += (rnd() - 0.5) * 1.3;
    d.z += (rnd() - 0.5) * 1.3;
    d.y += 0.4;
    branch(geos, tip, d, len * (0.62 + rnd() * 0.2), r * 0.72, depth - 1, a, b, maxH);
  }
}

function lattice(size) {
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const u = x / size - 0.5, v = y / size;
      const ang = Math.atan2(u, v + 0.05);
      const rad = Math.hypot(u, v + 0.05);
      const ribs = Math.abs(Math.sin(ang * 26)) < 0.18;
      const rings = Math.abs(Math.sin(rad * 70 + Math.sin(ang * 9) * 0.8)) < 0.22;
      const inside = rad < 0.95 && rad > 0.04;
      const i = (y * size + x) * 4;
      data[i] = data[i + 1] = data[i + 2] = 255;
      data[i + 3] = inside && (ribs || rings) ? 255 : 0;
    }
  }
  const t = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  t.magFilter = THREE.LinearFilter;
  t.needsUpdate = true;
  return t;
}

function tentacles(count, radius, len, a, b, thick = 0.035) {
  const geos = [];
  for (let i = 0; i < count; i++) {
    const ang = (i / count) * Math.PI * 2 + rnd() * 0.3;
    const rr = radius * (0.3 + rnd() * 0.7);
    const l = len * (0.7 + rnd() * 0.5);
    const g = new THREE.CylinderGeometry(thick * 0.3, thick, l, 5, 4);
    g.translate(0, l / 2, 0);
    g.rotateZ(Math.cos(ang) * 0.5);
    g.rotateX(Math.sin(ang) * 0.5);
    g.translate(Math.cos(ang) * rr, 0, Math.sin(ang) * rr);
    geos.push(g);
  }
  const m = merge(geos.map((g) => paint(g, a, b, len)));
  return m;
}

const C = (hex) => new THREE.Color(hex);

// Each builder returns the parts of one piece: { geo, sway, emissive?, map? } and, for bubblers, a source height.
const BUILD = {
  branch(item) {
    const geos = [];
    const a = C(item.color), b = C(item.tip);
    for (let k = 0; k < 3; k++) {
      const d = new THREE.Vector3((rnd() - 0.5) * 0.6, 1, (rnd() - 0.5) * 0.6);
      branch(geos, new THREE.Vector3((rnd() - 0.5) * 0.4, -0.05, (rnd() - 0.5) * 0.3), d, 0.55, 0.11, 3, a, b, 1.6);
    }
    for (const g of geos) if (!g.index) g.computeVertexNormals();
    return [{ geo: merge(geos.map((g) => paint(g, a.clone().multiplyScalar(0.8), b, 1.7, 1.4))), sway: 0 }];
  },
  brain(item) {
    const g = new THREE.IcosahedronGeometry(0.8, 5);
    const p = g.attributes.position;
    const col = new Float32Array(p.count * 3);
    const v = new THREE.Vector3();
    const a = C(item.color), b = C(item.tip), c = new THREE.Color();
    for (let i = 0; i < p.count; i++) {
      v.fromBufferAttribute(p, i);
      const groove = Math.sin(v.x * 11 + Math.sin(v.z * 7) * 1.6) * Math.sin(v.z * 10 + Math.sin(v.y * 8) * 1.4);
      const k = Math.abs(groove) < 0.25 ? 0.93 : 1;
      v.multiplyScalar(k);
      if (v.y < 0) v.y *= 0.3;
      v.y *= 0.72;
      p.setXYZ(i, v.x, v.y, v.z);
      c.copy(k < 1 ? b : a);
      col.set([c.r, c.g, c.b], i * 3);
    }
    g.computeVertexNormals();
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    g.setAttribute("aBend", new THREE.BufferAttribute(new Float32Array(p.count), 1));
    return [{ geo: g, sway: 0 }];
  },
  fan(item) {
    const g = new THREE.CircleGeometry(1.5, 32, Math.PI * 0.08, Math.PI * 0.84);
    g.translate(0, 0.05, 0);
    const p = g.attributes.position;
    const uv = g.attributes.uv;
    for (let i = 0; i < p.count; i++) uv.setXY(i, p.getX(i) / 3 + 0.5, p.getY(i) / 1.55);
    g.computeVertexNormals();
    paint(g, C(item.color), C(item.tip), 1.5);
    const stem = paint(new THREE.CylinderGeometry(0.04, 0.07, 0.4, 6).translate(0, 0.1, 0), C(item.color), C(item.color), 1.5);
    return [{ geo: g, sway: 0.28, map: lattice(256), double: true }, { geo: merge([stem]), sway: 0 }];
  },
  arch(item) {
    const g = lumpy(new THREE.TorusGeometry(1.1, 0.34, 12, 28, Math.PI), 0.16, 3.1);
    g.scale(1, 1.05, 0.9);
    return [{ geo: merge([paint(g, C(item.color).multiplyScalar(0.7), C(item.tip), 1.4)]), sway: 0 }];
  },
  anemone(item) {
    const base = paint(new THREE.CylinderGeometry(0.32, 0.4, 0.3, 14).translate(0, 0.15, 0), C(item.color).multiplyScalar(0.7), C(item.color), 0.3);
    const tent = tentacles(46, 0.32, 0.75, C(item.color), C(item.tip));
    tent.translate(0, 0.25, 0);
    const glow = item.theme === "deep";
    return [{ geo: merge([base]), sway: 0 }, { geo: tent, sway: 0.5, emissive: glow ? C(item.tip) : null }];
  },
  wood(item) {
    const geos = [];
    for (let k = 0; k < 3; k++) {
      const pts = [];
      const x0 = (rnd() - 0.5) * 0.6;
      for (let i = 0; i < 5; i++) {
        const t = i / 4;
        pts.push(new THREE.Vector3(x0 + t * (k - 1) * 1.1 + Math.sin(t * 3 + k) * 0.2, t * (1.2 + k * 0.5) + 0.05, (rnd() - 0.5) * 0.4 + t * 0.2));
      }
      const tube = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), 16, 0.12 - k * 0.025, 7, false);
      geos.push(paint(tube, C(item.color).multiplyScalar(0.7), C(item.tip), 2));
    }
    const log = new THREE.CylinderGeometry(0.16, 0.2, 2.2, 8, 4);
    log.rotateZ(Math.PI / 2 - 0.12);
    log.translate(0.2, 0.15, 0.1);
    geos.push(paint(lumpy(log, 0.05, 6), C(item.color).multiplyScalar(0.7), C(item.tip), 1));
    return [{ geo: merge(geos), sway: 0 }];
  },
  fern(item) {
    const geos = [];
    for (let i = 0; i < 11; i++) {
      const l = 0.7 + rnd() * 0.7;
      const g = new THREE.PlaneGeometry(0.22, l, 1, 6);
      const p = g.attributes.position;
      for (let j = 0; j < p.count; j++) {
        const t = (p.getY(j) + l / 2) / l;
        p.setX(j, p.getX(j) * Math.sin(Math.PI * Math.min(1, t * 1.1 + 0.05)));
        p.setZ(j, t * t * 0.4);
      }
      g.translate(0, l / 2, 0);
      g.rotateX(-0.25 - rnd() * 0.4);
      g.rotateY((i / 11) * Math.PI * 2 + rnd());
      g.computeVertexNormals();
      geos.push(paint(g, C(item.color).multiplyScalar(0.6), C(item.tip), 1.3));
    }
    return [{ geo: merge(geos), sway: 0.5, double: true }];
  },
  stones(item) {
    const geos = [];
    for (let i = 0; i < 6; i++) {
      const g = rock(C(item.tip).lerp(C(item.color), rnd()), 0.2 + rnd() * 0.25);
      g.translate((rnd() - 0.5) * 1.4, 0.05, (rnd() - 0.5) * 0.8);
      geos.push(g);
    }
    return [{ geo: merge(geos), sway: 0 }];
  },
  grass(item) {
    const geos = [];
    for (let i = 0; i < 22; i++) {
      const h = 0.8 + rnd() * 1.6;
      const g = new THREE.PlaneGeometry(0.07, h, 1, 6);
      g.translate(0, h / 2, 0);
      g.rotateY(rnd() * Math.PI);
      g.rotateZ((rnd() - 0.5) * 0.4);
      g.translate((rnd() - 0.5) * 0.6, 0, (rnd() - 0.5) * 0.4);
      g.computeVertexNormals();
      geos.push(paint(g, C(item.color).multiplyScalar(0.55), C(item.tip), 2.4));
    }
    return [{ geo: merge(geos), sway: 0.6, double: true }];
  },
  vent(item) {
    const pts = [];
    for (let i = 0; i <= 10; i++) {
      const t = i / 10;
      pts.push(new THREE.Vector2(0.55 * (1 - t) + 0.16 + Math.sin(t * 9) * 0.04, t * 1.7));
    }
    const g = lumpy(new THREE.LatheGeometry(pts, 14), 0.06, 7);
    const glow = new THREE.TorusGeometry(0.17, 0.035, 6, 16).rotateX(Math.PI / 2).translate(0, 1.7, 0);
    return [
      { geo: merge([paint(g, C(item.color), C(item.color).lerp(C(item.tip), 0.15), 1.7)]), sway: 0 },
      { geo: merge([paint(glow, C(item.tip), C(item.tip), 1)]), sway: 0, emissive: C(item.tip) },
    ];
  },
  worms(item) {
    const tubes = [], plumes = [];
    for (let i = 0; i < 12; i++) {
      const h = 0.6 + rnd() * 1.1;
      const x = (rnd() - 0.5) * 0.7, z = (rnd() - 0.5) * 0.5;
      const g = new THREE.CylinderGeometry(0.05, 0.065, h, 7, 4);
      g.translate(x, h / 2, z);
      tubes.push(paint(g, C(item.color).multiplyScalar(0.75), C(item.color), 1.8));
      const pl = new THREE.ConeGeometry(0.12, 0.22, 8, 2, true);
      pl.rotateX(Math.PI);
      pl.translate(x, h + 0.1, z);
      plumes.push(paint(pl, C(item.tip), C(item.tip), 1.8));
    }
    return [{ geo: merge(tubes), sway: 0.12 }, { geo: merge(plumes), sway: 0.14, emissive: C(item.tip).multiplyScalar(0.35) }];
  },
  bubbler(item) {
    const g = lumpy(new THREE.CylinderGeometry(0.22, 0.3, 0.32, 10, 2), 0.05, 8).translate(0, 0.16, 0);
    const cap = new THREE.TorusGeometry(0.14, 0.04, 6, 14).rotateX(Math.PI / 2).translate(0, 0.33, 0);
    return [{ geo: merge([paint(g, C(item.color), C(item.tip), 0.4), paint(cap, C(item.tip), C(item.tip), 0.4)]), sway: 0, bubbles: 0.36 }];
  },
};

const SLOTS = [
  { fx: -0.62, z: -1.5, s: 1 }, { fx: 0.56, z: -1.8, s: 1 }, { fx: 0.34, z: -0.6, s: 0.8 },
  { fx: -0.2, z: -2.3, s: 1.1 }, { fx: 0.8, z: 0.4, s: 0.8 }, { fx: -0.84, z: 0.6, s: 0.8 },
  { fx: 0.32, z: -2.4, s: 1 }, { fx: -0.42, z: 0.2, s: 0.7 }, { fx: 0.0, z: -1.2, s: 0.8 },
  { fx: 0.66, z: -0.6, s: 0.8 }, { fx: -0.7, z: -2.4, s: 1 }, { fx: 0.45, z: 1.2, s: 0.65 },
  { fx: -0.05, z: 1.5, s: 0.6 },
];

export function buildPiece(item) {
  reseed(item.id.length * 131 + item.price);
  const parts = BUILD[item.kind](item);
  const group = new THREE.Group();
  let bubbleY = 0;
  for (const part of parts) {
    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.8,
      metalness: 0,
      envMapIntensity: 0.5,
      side: part.double ? THREE.DoubleSide : THREE.FrontSide,
    });
    if (part.map) { mat.alphaMap = part.map; mat.alphaTest = 0.5; }
    if (part.emissive) { mat.emissive = part.emissive; mat.emissiveIntensity = 1.6; }
    patchMaterial(mat, { caustic: 1.1, sway: part.sway, key: `${item.kind}-${part.sway}-${part.double ? 1 : 0}-${part.map ? 1 : 0}` });
    const mesh = new THREE.Mesh(part.geo, mat);
    group.add(mesh);
    if (part.bubbles) bubbleY = part.bubbles;
  }
  if (item.kind === "vent") bubbleY = 1.75;
  group.userData.bubbleY = bubbleY;
  return group;
}

export function createDecor(catalog, theme, pal) {
  const group = new THREE.Group();
  const pieces = new Map();
  const rocks = new THREE.Group();
  group.add(rocks);
  const rockMat = patchMaterial(new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9, envMapIntensity: 0.4 }), { caustic: 1.3, key: "rock" });
  const sources = [];

  function layout(frame, owned) {
    const half = (frame.backRect.x1 - frame.backRect.x0) * 0.5 * 0.82;
    const narrow = frame.aspect < 0.8;
    rocks.clear();
    reseed(theme.length * 977);
    const spots = narrow
      ? [[-0.8, DEPTH_BACK + 0.6, 0.9], [0.85, DEPTH_BACK + 0.9, 1.0], [0.1, DEPTH_BACK + 0.4, 0.7], [-0.9, 1.2, 0.5]]
      : [[-0.92, DEPTH_BACK + 0.8, 1.2], [-0.78, DEPTH_BACK + 1.6, 0.8], [0.9, DEPTH_BACK + 0.7, 1.3], [0.42, DEPTH_BACK + 0.3, 0.8], [-0.3, DEPTH_BACK + 0.2, 0.6], [0.97, 1.0, 0.6]];
    const geos = spots.map(([fx, z, s]) => {
      const g = rock(pal.rock, s);
      const x = fx * half;
      g.translate(x, sandHeight(x, z) - 0.1, z);
      return g;
    });
    rocks.add(new THREE.Mesh(merge(geos), rockMat));

    sources.length = 0;
    const wanted = new Set(owned);
    for (const [id, piece] of pieces) {
      if (!wanted.has(id)) { group.remove(piece); pieces.delete(id); }
    }
    owned.forEach((id, i) => {
      const item = catalog.decor.find((d) => d.id === id);
      if (!item) return;
      let piece = pieces.get(id);
      if (!piece) {
        piece = buildPiece(item);
        pieces.set(id, piece);
        group.add(piece);
      }
      const slot = SLOTS[i % SLOTS.length];
      const x = slot.fx * half * (narrow ? 0.9 : 1);
      const z = narrow ? slot.z * 0.8 : slot.z;
      const s = slot.s * (narrow ? 1.05 : 1.45);
      piece.position.set(x, sandHeight(x, z) - 0.05, z);
      piece.scale.setScalar(s);
      piece.rotation.y = (i * 1.7) % (Math.PI * 2) - 0.4;
      if (piece.userData.bubbleY) sources.push(new THREE.Vector3(x, piece.position.y + piece.userData.bubbleY * s, z));
    });
  }

  return { group, layout, sources };
}
