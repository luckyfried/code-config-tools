// The town's landmarks and the desert around it: a turning windmill, a water tower, a church steeple, a covered
// wagon, telegraph poles running to the horizon, saguaros, scrub, rocks, and the mesas that close the view.
import * as THREE from "three";
import { box, cylinder, xf, seeded } from "./kit.js";

export function buildLandmarks(kit, tokens) {
  const wood = tokens.wood;
  const woodLight = tokens.woodLight;
  const dark = tokens.wood.clone().multiplyScalar(0.4);
  const metal = new THREE.Color(0.34, 0.33, 0.32);

  // water tower, left, peeking over the roofs
  {
    const x = -17;
    const z = -30;
    const legH = 8.5;
    for (const [dx, dz] of [[-1.6, -1.6], [1.6, -1.6], [-1.6, 1.6], [1.6, 1.6]]) {
      kit.add("plain", box(0.26, legH + 0.4, 0.26), wood, xf(x + dx * 1.05, (legH + 0.4) / 2, z + dz * 1.05, dz * 0.03, 0, -dx * 0.03));
    }
    for (const y of [2.6, 5.4]) {
      for (const [dx, dz, ry] of [[0, -1.6, 0], [0, 1.6, 0], [-1.6, 0, Math.PI / 2], [1.6, 0, Math.PI / 2]]) {
        kit.add("plain", box(3.4, 0.14, 0.12), wood, xf(x + dx, y, z + dz, 0, ry, 0));
        kit.add("plain", box(4.1, 0.08, 0.08), wood, xf(x + dx, y + 1.4, z + dz, 0, ry, 0.72));
      }
    }
    kit.add("wood", box(4.6, 0.3, 4.6), woodLight, xf(x, legH + 0.15, z));
    const tank = cylinder(2.3, 2.45, 3.6, 24);
    kit.add("wood", tank, woodLight.clone().multiplyScalar(0.92), xf(x, legH + 2.1, z, 0, 0, Math.PI / 2 * 0));
    for (const y of [0.5, 1.6, 2.8]) kit.add("metal", cylinder(2.47 - y * 0.03, 2.47 - y * 0.03, 0.08, 24), dark, xf(x, legH + 0.3 + y, z));
    kit.add("tin", new THREE.ConeGeometry(2.7, 1.5, 24, 1), metal, xf(x, legH + 4.65, z));
    kit.add("metal", cylinder(0.05, 0.05, 1.0, 6), dark, xf(x, legH + 5.9, z));
    // spout
    kit.add("metal", cylinder(0.12, 0.12, 2.4, 8), dark, xf(x + 2.1, legH + 0.2, z, 0, 0, 0.9));
  }

  // church at the far end of the left side, steeple against the sky
  {
    const x = -15;
    const z = -112;
    kit.add("wood", box(9, 6.5, 14), tokens.paint2.clone().multiplyScalar(1.02), xf(x, 3.25, z));
    const roof = new THREE.Shape();
    roof.moveTo(-5, 0);
    roof.lineTo(5, 0);
    roof.lineTo(0, 3.6);
    roof.lineTo(-5, 0);
    const rg = new THREE.ExtrudeGeometry(roof, { depth: 14.4, bevelEnabled: false });
    kit.add("wood", rg, wood.clone().multiplyScalar(0.8), xf(x, 6.5, z + 7.2, 0, 0, 0));
    kit.add("wood", box(3.2, 6, 3.2), tokens.paint2, xf(x + 2.5, 9, z + 5.5));
    kit.add("wood", box(3.6, 0.3, 3.6), tokens.trim, xf(x + 2.5, 12, z + 5.5));
    kit.add("wood", box(2.4, 2.2, 2.4), tokens.paint2, xf(x + 2.5, 13.2, z + 5.5));
    kit.add("glass", box(2.5, 1.2, 0.8), tokens.window, xf(x + 2.5, 13.2, z + 5.5));
    kit.add("wood", new THREE.ConeGeometry(2.0, 5.0, 4, 1), wood.clone().multiplyScalar(0.7), xf(x + 2.5, 16.8, z + 5.5, 0, Math.PI / 4, 0));
    kit.add("plain", box(0.12, 1.4, 0.12), dark, xf(x + 2.5, 19.9, z + 5.5));
    kit.add("plain", box(0.12, 0.12, 0.8), dark, xf(x + 2.5, 20.2, z + 5.5));
  }

  // covered wagon parked on the right, past the saloon
  {
    const x = 5.2;
    const z = -24;
    const ry = -0.18;
    const m = new THREE.Matrix4().compose(new THREE.Vector3(x, 0, z), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, ry, 0)), new THREE.Vector3(1, 1, 1));
    const at = (lx, ly, lz, rx = 0, ryy = 0, rz = 0) => new THREE.Matrix4().multiplyMatrices(m, xf(lx, ly, lz, rx, ryy, rz));
    kit.add("wood", box(1.7, 0.5, 4.2), woodLight, at(0, 1.05, 0));
    kit.add("plain", box(0.12, 0.12, 2.6), dark, at(0, 0.62, 3.2));
    for (const [wx, wz, r] of [[-0.95, -1.4, 0.72], [0.95, -1.4, 0.72], [-0.95, 1.5, 0.55], [0.95, 1.5, 0.55]]) {
      kit.add("plain", new THREE.TorusGeometry(r, 0.05, 6, 24), dark, at(wx, r, wz, 0, Math.PI / 2, 0));
      for (let k = 0; k < 6; k += 1) kit.add("plain", box(0.04, r * 2, 0.05), woodLight, at(wx, r, wz, (k * Math.PI) / 6, 0, 0));
      kit.add("plain", cylinder(0.09, 0.09, 0.14, 8), dark, at(wx, r, wz, 0, 0, Math.PI / 2));
    }
    const cover = new THREE.CylinderGeometry(1.05, 1.05, 3.8, 18, 1, true, -Math.PI / 2, Math.PI);
    kit.add("cloth", cover, new THREE.Color(0.93, 0.89, 0.8).lerp(tokens.trim, 0.4), at(0, 1.3, 0, Math.PI / 2, 0, 0));
    for (const hz of [-1.7, -0.6, 0.6, 1.7]) kit.add("plain", new THREE.TorusGeometry(1.06, 0.03, 4, 18, Math.PI), wood, at(0, 1.3, hz));
  }
}

/** A turning windmill on the right, its wheel a separate mesh so it can spin. */
export function createWindmill(kit, tokens, materials) {
  const x = 20;
  const z = -50;
  const h = 12.5;
  const wood = tokens.wood;
  const dark = tokens.wood.clone().multiplyScalar(0.4);
  for (const [dx, dz] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
    kit.add("plain", box(0.2, h + 0.2, 0.2), wood, xf(x + dx * 1.15, h / 2, z + dz * 1.15, dz * 0.085, 0, -dx * 0.085));
  }
  for (let i = 1; i < 6; i += 1) {
    const y = (i * h) / 6;
    const spread = 2.3 * (1 - (y / h) * 0.82);
    for (const [ry, dx, dz] of [[0, 0, -1], [0, 0, 1], [Math.PI / 2, -1, 0], [Math.PI / 2, 1, 0]]) {
      kit.add("plain", box(spread * 2, 0.1, 0.1), wood, xf(x + dx * spread, y, z + dz * spread, 0, ry, 0));
    }
  }
  kit.add("wood", box(1.0, 0.18, 1.0), wood, xf(x, h, z));
  kit.add("metal", box(0.5, 0.5, 1.2), dark, xf(x, h + 0.35, z));
  // tail vane
  kit.add("metal", box(0.06, 0.06, 2.6), dark, xf(x + 0.2, h + 0.4, z - 1.6, 0, 0.55, 0));
  kit.add("tin", box(0.04, 1.1, 1.6), new THREE.Color(0.6, 0.58, 0.55), xf(x + 0.85, h + 0.5, z - 2.6, 0, 0.55, 0));

  // the wheel
  const wheel = new THREE.Group();
  const parts = [];
  const blades = 18;
  const R = 2.3;
  const bladeColor = new THREE.Color(0.62, 0.6, 0.57);
  for (let i = 0; i < blades; i += 1) {
    const a = (i / blades) * Math.PI * 2;
    const g = box(0.38, 1.5, 0.03);
    g.rotateY(0.45);
    g.translate(0, R - 0.85, 0);
    g.rotateZ(a);
    parts.push(g);
  }
  const ring = new THREE.TorusGeometry(R - 0.12, 0.04, 6, 36);
  const ring2 = new THREE.TorusGeometry(R - 1.55, 0.035, 6, 24);
  const hub = cylinder(0.18, 0.18, 0.3, 10);
  hub.rotateX(Math.PI / 2);
  const geo = [...parts, ring, ring2, hub].map((g) => (g.index ? g.toNonIndexed() : g));
  for (const g of geo) {
    for (const name of Object.keys(g.attributes)) if (!["position", "normal", "uv"].includes(name)) g.deleteAttribute(name);
    if (!g.attributes.uv) g.setAttribute("uv", new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
  }
  const merged = mergeAll(geo);
  const mesh = new THREE.Mesh(merged, new THREE.MeshStandardMaterial({ color: bladeColor, roughness: 0.6, metalness: 0.35, side: THREE.DoubleSide, envMapIntensity: 0.8 }));
  mesh.castShadow = true;
  wheel.add(mesh);
  wheel.position.set(x - 0.15, h + 0.35, z + 0.75);
  wheel.rotation.y = 0.55;
  return wheel;
}

function mergeAll(list) {
  let count = 0;
  for (const g of list) count += g.attributes.position.count;
  const pos = new Float32Array(count * 3);
  const nor = new Float32Array(count * 3);
  const uv = new Float32Array(count * 2);
  let o = 0;
  for (const g of list) {
    pos.set(g.attributes.position.array, o * 3);
    nor.set(g.attributes.normal.array, o * 3);
    uv.set(g.attributes.uv.array, o * 2);
    o += g.attributes.position.count;
  }
  const out = new THREE.BufferGeometry();
  out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  out.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  out.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  return out;
}

/** Telegraph poles down the left of the trail, wires sagging between them to the horizon. */
export function buildPoles(kit, tokens) {
  const wood = tokens.wood.clone().multiplyScalar(0.85);
  const wire = tokens.wood.clone().multiplyScalar(0.3);
  const poles = [];
  for (let i = 0; i < 26; i += 1) {
    const z = -96 - i * 26;
    const bend = Math.sin(z * 0.011) * 4.0 * Math.min(1, (-z - 112) / 38 + 0.0);
    const x = -10.5 + (z < -112 ? bend : 0);
    poles.push(new THREE.Vector3(x, 0, z));
    kit.add("plain", cylinder(0.11, 0.14, 7.4, 6), wood, xf(x, 3.7, z));
    kit.add("plain", box(1.6, 0.12, 0.12), wood, xf(x, 6.9, z));
    for (const dx of [-0.65, 0, 0.65]) kit.add("glass", cylinder(0.04, 0.05, 0.14, 6), new THREE.Color(0.35, 0.55, 0.5), xf(x + dx, 7.02, z));
  }
  for (let i = 0; i < poles.length - 1; i += 1) {
    const a = poles[i];
    const b = poles[i + 1];
    for (const dx of [-0.65, 0, 0.65]) {
      const curve = new THREE.QuadraticBezierCurve3(
        new THREE.Vector3(a.x + dx, 7.06, a.z),
        new THREE.Vector3((a.x + b.x) / 2 + dx, 6.3, (a.z + b.z) / 2),
        new THREE.Vector3(b.x + dx, 7.06, b.z),
      );
      kit.add("plain", new THREE.TubeGeometry(curve, 8, 0.015 + i * 0.002, 3, false), wire, null);
    }
  }
}

/** Saguaros: a trunk and a few arms that bend up, ribbed by their own geometry. */
function saguaro(kit, x, z, scale, color, rnd) {
  const trunkH = (3.2 + rnd() * 2.6) * scale;
  const r = 0.3 * scale;
  kit.add("plain", cylinder(r * 0.92, r, trunkH, 12), color, xf(x, trunkH / 2, z));
  kit.add("plain", new THREE.SphereGeometry(r * 0.92, 12, 6, 0, Math.PI * 2, 0, Math.PI / 2), color, xf(x, trunkH, z));
  const arms = 1 + Math.floor(rnd() * 3);
  for (let i = 0; i < arms; i += 1) {
    const side = i % 2 === 0 ? 1 : -1;
    const ry = rnd() * Math.PI * 2;
    const ay = trunkH * (0.35 + rnd() * 0.3);
    const out = 0.55 * scale;
    const up = (0.8 + rnd() * 1.3) * scale;
    const ar = r * 0.68;
    const dir = new THREE.Vector3(Math.cos(ry) * side, 0, Math.sin(ry) * side);
    // elbow going out, then the arm going up
    kit.add("plain", cylinder(ar, ar, out, 10), color, xf(x + dir.x * out * 0.5, ay, z + dir.z * out * 0.5, 0, -Math.atan2(dir.z, dir.x), Math.PI / 2));
    kit.add("plain", new THREE.SphereGeometry(ar, 10, 6), color, xf(x + dir.x * out, ay, z + dir.z * out));
    kit.add("plain", cylinder(ar * 0.95, ar, up, 10), color, xf(x + dir.x * out, ay + up / 2, z + dir.z * out));
    kit.add("plain", new THREE.SphereGeometry(ar * 0.95, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2), color, xf(x + dir.x * out, ay + up, z + dir.z * out));
  }
}

export function buildDesert(kit, tokens) {
  const rnd = seeded(77);
  const cactus = new THREE.Color(0.24, 0.33, 0.2).lerp(tokens.ambientGround, 0.15);
  const spots = [
    [-13.5, -6, 1.0], [14.5, 10, 0.9], [-24, -60, 1.2], [26, -78, 1.1], [-30, -128, 1.4], [18, -140, 1.3],
    [-42, -170, 1.6], [36, -200, 1.5], [-12, -230, 1.3], [60, -260, 1.8], [-70, -300, 2.0], [22, -330, 1.6],
  ];
  for (const [x, z, s] of spots) saguaro(kit, x, z, s, cactus.clone().multiplyScalar(0.85 + rnd() * 0.3), rnd);
  // fence posts at the edge of town
  for (let i = 0; i < 9; i += 1) {
    const z = -100 - i * 3;
    kit.add("plain", box(0.14, 1.2, 0.14), tokens.wood, xf(15 + rnd() * 0.2, 0.6, z, 0, 0, (rnd() - 0.5) * 0.12));
    if (i < 8) kit.add("plain", box(0.08, 0.1, 3.0), tokens.woodLight, xf(15.05, 0.95, z - 1.5));
  }
}

/** Scrub and rocks as instanced meshes, scattered with a fixed seed. */
export function createScatter(tokens, tier) {
  const rnd = seeded(91);
  const group = new THREE.Group();
  const scrubGeo = new THREE.IcosahedronGeometry(0.5, 1);
  scrubGeo.scale(1, 0.55, 1);
  const scrub = new THREE.InstancedMesh(scrubGeo, new THREE.MeshStandardMaterial({ roughness: 1, flatShading: true, envMapIntensity: 0.3 }), 220);
  const rockGeo = new THREE.DodecahedronGeometry(0.6, 0);
  const rock = new THREE.InstancedMesh(rockGeo, new THREE.MeshStandardMaterial({ roughness: 0.95, flatShading: true, envMapIntensity: 0.3 }), 140);
  const m = new THREE.Matrix4();
  const q = new THREE.Quaternion();
  const e = new THREE.Euler();
  const p = new THREE.Vector3();
  const s = new THREE.Vector3();
  const sage = new THREE.Color(0.42, 0.44, 0.3);
  const place = (mesh, count, colorA, colorB, sizeMin, sizeMax) => {
    for (let i = 0; i < count; i += 1) {
      let x;
      let z;
      do {
        z = 20 - Math.pow(rnd(), 1.4) * 620;
        x = (rnd() - 0.5) * 2 * (24 + (-z) * 0.9);
      } while ((Math.abs(x) < 26 && z > -110) || Math.abs(x - Math.sin(z * 0.011) * 4) < 7);
      const k = sizeMin + rnd() * (sizeMax - sizeMin);
      p.set(x, k * 0.15, z);
      e.set(rnd() * 0.4, rnd() * Math.PI * 2, rnd() * 0.4);
      q.setFromEuler(e);
      s.set(k * (0.8 + rnd() * 0.5), k, k * (0.8 + rnd() * 0.5));
      m.compose(p, q, s);
      mesh.setMatrixAt(i, m);
      mesh.setColorAt(i, colorA.clone().lerp(colorB, rnd()));
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  };
  place(scrub, 220, sage.clone().lerp(tokens.ambientGround, 0.3), tokens.ground.clone().multiplyScalar(0.7), 0.6, 2.0);
  place(rock, 140, tokens.mesa.clone().multiplyScalar(0.8), tokens.ground.clone().multiplyScalar(0.75), 0.4, 2.6);
  scrub.castShadow = rock.castShadow = true;
  scrub.receiveShadow = rock.receiveShadow = true;
  group.add(scrub, rock);
  return group;
}

/** Mesas and buttes on the horizon: flat tops, steep faces, and talus skirts, softened by the haze. */
export function buildMesas(kit, tokens) {
  const rnd = seeded(13);
  const ring = [
    [-520, -760, 260, 110], [-260, -900, 180, 70], [-80, -980, 110, 46], [150, -940, 150, 62],
    [380, -820, 280, 120], [640, -600, 220, 95], [-760, -520, 240, 85], [20, -1100, 340, 58],
  ];
  for (const [x, z, w, h] of ring) {
    const shape = new THREE.Shape();
    const talus = w * 0.22;
    const cap = w * (0.32 + rnd() * 0.2);
    shape.moveTo(-w / 2 - talus, 0);
    shape.quadraticCurveTo(-w / 2, h * 0.08, -cap / 2 - w * 0.06, h * 0.42);
    shape.lineTo(-cap / 2 - w * 0.02, h * 0.82);
    shape.lineTo(-cap / 2, h);
    for (let i = 1; i < 6; i += 1) shape.lineTo(-cap / 2 + (cap * i) / 6, h - rnd() * h * 0.03);
    shape.lineTo(cap / 2, h);
    shape.lineTo(cap / 2 + w * 0.03, h * 0.78);
    shape.lineTo(cap / 2 + w * 0.08, h * 0.4);
    shape.quadraticCurveTo(w / 2, h * 0.08, w / 2 + talus, 0);
    shape.lineTo(-w / 2 - talus, 0);
    const g = new THREE.ExtrudeGeometry(shape, { depth: w * 0.6, bevelEnabled: false, curveSegments: 6 });
    g.translate(0, 0, -w * 0.3);
    kit.add("mesa", g, tokens.mesa.clone().offsetHSL(0, 0, (rnd() - 0.5) * 0.06), xf(x, -2, z, 0, (rnd() - 0.5) * 0.5, 0));
  }
}
