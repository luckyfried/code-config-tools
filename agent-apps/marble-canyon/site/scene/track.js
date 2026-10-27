// The banked ribbon, built along the track's frames in chunks (so the camera only draws what it faces), with the
// kerbs, boost tiles, gates, start and finish lines, and support pylons placed along the same frames.
import {
  BoxGeometry,
  BufferAttribute,
  BufferGeometry,
  CanvasTexture,
  CylinderGeometry,
  DoubleSide,
  Group,
  InstancedMesh,
  Matrix4,
  Mesh,
  MeshStandardMaterial,
  PlaneGeometry,
  SRGBColorSpace,
  Vector3,
} from "three";
import { HALF_WIDTH, KERB, PAD_HALF, PAD_LENGTH, DISH, frameAt, newFrame, surfaceHeight } from "../game/generate.js";
import { frameMatrix, mergeGeometries } from "./objects.js";

const W = HALF_WIDTH;
const LIP = 1.1;
const BASE = -0.55;
const CHUNK = 110;
const TOP_U = [-1, -0.95, -0.9, -0.78, -0.64, -0.5, -0.36, -0.22, -0.1, 0, 0.1, 0.22, 0.36, 0.5, 0.64, 0.78, 0.9, 0.95, 1];
const TILE = 7;

// Cross-section pieces in (lateral, height) with the material group each belongs to.
function profile() {
  const top = TOP_U.map((u) => [u * W, surfaceHeight(u)]);
  const rim = surfaceHeight(1);
  const laneLeft = [
    [-W * LIP, rim],
    [-W, rim],
  ];
  const laneRight = [
    [W, rim],
    [W * LIP, rim],
  ];
  const side = [
    [W * LIP, rim],
    [W * LIP + 0.08, BASE],
    [0, BASE - 0.15],
    [-W * LIP - 0.08, BASE],
    [-W * LIP, rim],
  ];
  return { top, laneLeft, laneRight, side };
}

function segments(track) {
  const out = [];
  let a = track.first;
  for (const gap of track.gaps) {
    out.push([a, gap.s0]);
    a = gap.s1;
  }
  out.push([a, track.last]);
  const chunks = [];
  for (const [s0, s1] of out) {
    const pieces = Math.max(1, Math.round((s1 - s0) / CHUNK));
    for (let k = 0; k < pieces; k += 1) {
      chunks.push({ a: s0 + ((s1 - s0) * k) / pieces, b: s0 + ((s1 - s0) * (k + 1)) / pieces, capA: k === 0, capB: k === pieces - 1 });
    }
  }
  return chunks;
}

function buildChunk(track, chunk, step, shape) {
  const f = newFrame();
  const rows = [];
  const n = Math.max(2, Math.ceil((chunk.b - chunk.a) / step) + 1);
  for (let i = 0; i < n; i += 1) {
    const s = chunk.a + ((chunk.b - chunk.a) * i) / (n - 1);
    const fr = frameAt(track, s, f);
    rows.push({ s, p: [...fr.p], r: [...fr.r], n: [...fr.n] });
  }
  const pos = [];
  const uvs = [];
  const idx = [];
  const groups = [];
  const strip = (points, material, uOf) => {
    const start = idx.length;
    const base = pos.length / 3;
    const cols = points.length;
    for (const row of rows) {
      for (let c = 0; c < cols; c += 1) {
        const [l, h] = points[c];
        pos.push(row.p[0] + row.r[0] * l + row.n[0] * h, row.p[1] + row.r[1] * l + row.n[1] * h, row.p[2] + row.r[2] * l + row.n[2] * h);
        uvs.push(uOf(c, l, h), row.s / TILE);
      }
    }
    for (let i = 0; i < rows.length - 1; i += 1) {
      for (let c = 0; c < cols - 1; c += 1) {
        const a = base + i * cols + c;
        const b = a + cols;
        idx.push(a, a + 1, b, a + 1, b + 1, b);
      }
    }
    groups.push({ start, count: idx.length - start, material });
  };
  strip(shape.top, 0, (c) => c / (shape.top.length - 1));
  strip(shape.laneLeft, 1, () => 0.5);
  strip(shape.laneRight, 1, () => 0.5);
  strip(shape.side, 2, (c, l) => l * 0.1);

  // End caps where the ribbon stops at a jump lip or at either end of the track.
  const cap = (row, flip) => {
    const ring = [...shape.top, [W * LIP, surfaceHeight(1)], ...shape.side.slice(1, -1), [-W * LIP, surfaceHeight(1)]];
    const center = pos.length / 3;
    const start = idx.length;
    pos.push(row.p[0] + row.n[0] * -0.1, row.p[1] + row.n[1] * -0.1, row.p[2] + row.n[2] * -0.1);
    uvs.push(0.5, 0.5);
    for (const [l, h] of ring) {
      pos.push(row.p[0] + row.r[0] * l + row.n[0] * h, row.p[1] + row.r[1] * l + row.n[1] * h, row.p[2] + row.r[2] * l + row.n[2] * h);
      uvs.push(l * 0.1, h * 0.1);
    }
    for (let k = 0; k < ring.length; k += 1) {
      const a = center + 1 + k;
      const b = center + 1 + ((k + 1) % ring.length);
      if (flip) idx.push(center, b, a);
      else idx.push(center, a, b);
    }
    groups.push({ start, count: idx.length - start, material: 2 });
  };
  if (chunk.capA) cap(rows[0], false);
  if (chunk.capB) cap(rows[rows.length - 1], true);

  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(pos), 3));
  geometry.setAttribute("uv", new BufferAttribute(new Float32Array(uvs), 2));
  geometry.setIndex(idx);
  for (const g of groups) geometry.addGroup(g.start, g.count, g.material);
  geometry.computeVertexNormals();
  geometry.computeBoundingSphere();
  return geometry;
}

// A painted sign for a gate: its number, or a checker for the start and finish.
function signTexture(label, accentCss) {
  const c = document.createElement("canvas");
  c.width = 512;
  c.height = 128;
  const ctx = c.getContext("2d");
  if (label === "checker") {
    const s = 32;
    for (let y = 0; y < 4; y += 1) {
      for (let x = 0; x < 16; x += 1) {
        ctx.fillStyle = (x + y) % 2 ? "rgb(20 20 24)" : "rgb(245 245 245)";
        ctx.fillRect(x * s, y * s, s, s);
      }
    }
  } else {
    ctx.fillStyle = "rgb(250 248 244)";
    ctx.fillRect(0, 0, 512, 128);
    ctx.fillStyle = accentCss;
    ctx.fillRect(0, 0, 512, 10);
    ctx.fillRect(0, 118, 512, 10);
    ctx.font = "800 84px 'National Park', system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "rgb(24 18 14)";
    ctx.fillText(label, 256, 68);
  }
  const tex = new CanvasTexture(c);
  tex.colorSpace = SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

export function createTrack(track, materials, tier, tokens) {
  const group = new Group();
  const shape = profile();
  const chunkMaterials = [materials.track, materials.lane, materials.trackSide];
  const chunks = [];
  for (const chunk of segments(track)) {
    const mesh = new Mesh(buildChunk(track, chunk, tier.trackStep, shape), chunkMaterials);
    mesh.receiveShadow = tier.shadows;
    mesh.userData.s = [chunk.a, chunk.b];
    chunks.push(mesh);
    group.add(mesh);
  }

  const f = newFrame();
  const m = new Matrix4();
  const p = [0, 0, 0];
  const place = (s, l, h) => {
    const fr = frameAt(track, s, f);
    for (let k = 0; k < 3; k += 1) p[k] = fr.p[k] + fr.r[k] * l + fr.n[k] * h;
    return fr;
  };

  // Kerbs: through every real turn on both sides, and on the lips and landings of the jumps.
  const kerbSpots = [];
  const kerbStep = 2;
  const nearGap = (s) => track.gaps.some((g) => (s > g.s0 - 14 && s < g.s0 - 0.8) || (s > g.s1 + 0.8 && s < g.s1 + 8));
  const inGap = (s) => track.gaps.some((g) => s > g.s0 - 0.8 && s < g.s1 + 0.8);
  for (let s = track.first + 2; s < track.last - 2; s += kerbStep) {
    if (inGap(s)) continue;
    const fr = frameAt(track, s, f);
    if (Math.abs(fr.curvature) > 0.0075 || nearGap(s)) kerbSpots.push(s);
  }
  const kerbGeometry = new BoxGeometry(1.75, 0.22, 0.42);
  const kerbs = new InstancedMesh(kerbGeometry, materials.kerb, kerbSpots.length * 2);
  const colorA = tokens.kerbA.clone();
  const colorB = tokens.kerbB.clone();
  let k = 0;
  for (const s of kerbSpots) {
    for (const side of [-1, 1]) {
      const fr = place(s, side * W * (1 + (LIP - 1) * 0.5), surfaceHeight(1) + 0.1);
      kerbs.setMatrixAt(k, frameMatrix(m, fr, p));
      kerbs.setColorAt(k, Math.floor(k / 2) % 2 ? colorA : colorB);
      k += 1;
    }
  }
  kerbs.count = k;
  kerbs.castShadow = false;
  kerbs.receiveShadow = tier.shadows;
  group.add(kerbs);

  // Boost tiles: chevrons laid in the dish at each pad's lane, tilted to the dish under them.
  const tileLength = 1.5;
  const tilesPerPad = Math.round(PAD_LENGTH / tileLength);
  const half = PAD_HALF * W;
  const tileGeometry = new BufferGeometry();
  tileGeometry.setAttribute(
    "position",
    new BufferAttribute(new Float32Array([-tileLength / 2, 0, -half, tileLength / 2, 0, -half, tileLength / 2, 0, half, -tileLength / 2, 0, half]), 3),
  );
  tileGeometry.setAttribute("normal", new BufferAttribute(new Float32Array([0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0]), 3));
  tileGeometry.setAttribute("uv", new BufferAttribute(new Float32Array([0, 0, 0, 1, 1, 1, 1, 0]), 2));
  tileGeometry.setIndex([0, 2, 1, 0, 3, 2]);
  const tiles = new InstancedMesh(tileGeometry, materials.boost, track.boosts.length * tilesPerPad);
  let t = 0;
  const tilt = newFrame();
  for (const pad of track.boosts) {
    for (let i = 0; i < tilesPerPad; i += 1) {
      const s = pad.s + (i + 0.5) * tileLength;
      const fr = place(s, pad.c * W, surfaceHeight(pad.c) + 0.035);
      const angle = Math.atan((2 * DISH * pad.c) / W);
      const c = Math.cos(angle);
      const sn = Math.sin(angle);
      for (let a = 0; a < 3; a += 1) {
        tilt.t[a] = fr.t[a];
        tilt.r[a] = fr.r[a] * c + fr.n[a] * sn;
        tilt.n[a] = fr.n[a] * c - fr.r[a] * sn;
      }
      tiles.setMatrixAt(t, frameMatrix(m, tilt, p));
      t += 1;
    }
  }
  tiles.receiveShadow = tier.shadows;
  group.add(tiles);

  // Gates: an arch with a numbered sign and a light curtain at the start, each checkpoint, and the finish.
  const span = W * LIP + 0.9;
  const archParts = [
    { geometry: new BoxGeometry(0.55, 7.2, 0.55), matrix: new Matrix4().makeTranslation(0, 3.6, -span) },
    { geometry: new BoxGeometry(0.55, 7.2, 0.55), matrix: new Matrix4().makeTranslation(0, 3.6, span) },
    { geometry: new BoxGeometry(0.7, 0.7, span * 2 + 0.55), matrix: new Matrix4().makeTranslation(0, 7.2, 0) },
    { geometry: new BoxGeometry(0.9, 0.35, 0.9), matrix: new Matrix4().makeTranslation(0, 0.18, -span) },
    { geometry: new BoxGeometry(0.9, 0.35, 0.9), matrix: new Matrix4().makeTranslation(0, 0.18, span) },
  ];
  const arch = mergeGeometries(archParts);
  const gateSpots = [{ s: 0, label: "checker" }, ...track.gates.map((g, i) => ({ s: g.s, label: `${i + 1}` })), { s: track.length, label: "checker" }];
  const arches = new InstancedMesh(arch, materials.gate, gateSpots.length);
  const accentCss = `#${tokens.accent.getHexString()}`;
  const curtains = [];
  const signGeometry = new PlaneGeometry(span * 1.3, span * 0.325);
  const curtainGeometry = new PlaneGeometry(span * 2, 6.6);
  gateSpots.forEach((spot, i) => {
    const fr = place(spot.s, 0, 0);
    arches.setMatrixAt(i, frameMatrix(m, fr, p));
    const sign = new Mesh(
      signGeometry,
      new MeshStandardMaterial({ map: signTexture(spot.label, accentCss), roughness: 0.5, side: DoubleSide }),
    );
    // The sign faces the oncoming marble, hung under the beam.
    const basis = new Matrix4().makeBasis(
      new Vector3(fr.r[0], fr.r[1], fr.r[2]),
      new Vector3(fr.n[0], fr.n[1], fr.n[2]),
      new Vector3(-fr.t[0], -fr.t[1], -fr.t[2]),
    );
    sign.quaternion.setFromRotationMatrix(basis);
    sign.position.set(p[0] + fr.n[0] * 6.1 - fr.t[0] * 0.4, p[1] + fr.n[1] * 6.1 - fr.t[1] * 0.4, p[2] + fr.n[2] * 6.1 - fr.t[2] * 0.4);
    group.add(sign);
    const curtain = new Mesh(curtainGeometry, materials.curtain.clone());
    curtain.quaternion.copy(sign.quaternion);
    curtain.position.set(p[0] + fr.n[0] * 3.4, p[1] + fr.n[1] * 3.4, p[2] + fr.n[2] * 3.4);
    curtain.userData.base = materials.curtain.opacity;
    group.add(curtain);
    curtains.push(curtain);
  });
  arches.castShadow = tier.shadows;
  arches.receiveShadow = tier.shadows;
  group.add(arches);

  // Checkered lines painted across the track at the start and the finish.
  const lineGeometry = new PlaneGeometry(W * 2.02, 1.6, 12, 1);
  lineGeometry.rotateX(-Math.PI / 2);
  lineGeometry.rotateY(Math.PI / 2);
  const lineMaterial = new MeshStandardMaterial({
    map: signTexture("checker", accentCss),
    roughness: 0.4,
    polygonOffset: true,
    polygonOffsetFactor: -2,
  });
  for (const s of [0, track.length]) {
    const fr = place(s, 0, 0);
    const line = new Mesh(lineGeometry.clone(), lineMaterial);
    const pos = line.geometry.attributes.position;
    for (let i = 0; i < pos.count; i += 1) {
      const across = pos.getZ(i) / W;
      pos.setY(i, surfaceHeight(Math.max(-1, Math.min(1, across))) + 0.03);
    }
    pos.needsUpdate = true;
    line.geometry.computeVertexNormals();
    line.matrixAutoUpdate = false;
    line.matrix.copy(frameMatrix(m, fr, p));
    line.receiveShadow = tier.shadows;
    group.add(line);
  }

  // Pylons from the ribbon's underside to the canyon floor.
  const pylonSpots = [];
  for (let s = track.first + 12; s < track.last - 8; s += 34) {
    if (track.gaps.some((g) => s > g.s0 - 6 && s < g.s1 + 6)) continue;
    pylonSpots.push(s);
  }
  const pylonGeometry = new CylinderGeometry(0.42, 0.7, 1, 7, 1);
  pylonGeometry.translate(0, -0.5, 0);
  const pylons = new InstancedMesh(pylonGeometry, materials.pylon, pylonSpots.length);
  pylonSpots.forEach((s, i) => {
    const fr = frameAt(track, s, f);
    const top = [fr.p[0] + fr.n[0] * BASE, fr.p[1] + fr.n[1] * BASE, fr.p[2] + fr.n[2] * BASE];
    m.makeScale(1, 24, 1);
    m.setPosition(top[0], top[1], top[2]);
    pylons.setMatrixAt(i, m);
  });
  group.add(pylons);

  return {
    group,
    chunks,
    kerbs,
    tiles,
    curtains,
    gateSpots,
    flashGate(index) {
      const curtain = curtains[index];
      if (curtain) curtain.userData.flash = 1;
    },
    update(dt) {
      materials.textures.arrows.offset.y -= dt * 1.6;
      for (const curtain of curtains) {
        const flash = curtain.userData.flash || 0;
        curtain.material.opacity = curtain.userData.base + flash * 0.55;
        if (flash > 0) curtain.userData.flash = Math.max(0, flash - dt * 1.8);
      }
    },
    applyColors(t) {
      const a = t.kerbA;
      const b = t.kerbB;
      for (let i = 0; i < kerbs.count; i += 1) kerbs.setColorAt(i, Math.floor(i / 2) % 2 ? a : b);
      if (kerbs.instanceColor) kerbs.instanceColor.needsUpdate = true;
      for (const curtain of curtains) curtain.material.color.copy(t.gate);
    },
  };
}

export { W as TRACK_HALF_WIDTH, LIP, KERB };
