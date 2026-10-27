// The canyon: terrain carved around the track by distance from it. A riverbed below the ribbon, terraced walls
// that rise from the floor on noise-displaced ridges either side, and a mesa top beyond, with boulders on the
// floor and hoodoos along the rims. Strata are read by height, so the layers run level across the whole canyon.
import {
  BufferAttribute,
  BufferGeometry,
  Color,
  CylinderGeometry,
  Group,
  IcosahedronGeometry,
  InstancedMesh,
  Matrix4,
  Mesh,
  PlaneGeometry,
  Quaternion,
  Vector3,
} from "three";
import { ImprovedNoise } from "three/addons/math/ImprovedNoise.js";
import { createRng, hashString } from "../game/rng.js";
import { mergeGeometries } from "./objects.js";

const TILE = 72;
const REACH = 150;
const FLOOR = 18;
const CELL = 32;
const BUCKET = 240;

const smoothstep = (a, b, x) => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

class TrackIndex {
  constructor(track, every = 3) {
    this.x = [];
    this.y = [];
    this.z = [];
    this.s = [];
    this.cells = new Map();
    for (let i = 0; i < track.count; i += every) {
      const k = this.x.length;
      this.x.push(track.px[i]);
      this.y.push(track.py[i]);
      this.z.push(track.pz[i]);
      this.s.push(track.first + i);
      const key = this.key(Math.floor(track.px[i] / CELL), Math.floor(track.pz[i] / CELL));
      if (!this.cells.has(key)) this.cells.set(key, []);
      this.cells.get(key).push(k);
    }
    this.out = { d: 0, y: 0, s: 0 };
  }

  key(cx, cz) {
    return cx * 73856093 + cz * 19349663;
  }

  nearest(x, z) {
    const cx = Math.floor(x / CELL);
    const cz = Math.floor(z / CELL);
    let best = Infinity;
    let bi = 0;
    for (let r = 0; r < 9; r += 1) {
      for (let i = -r; i <= r; i += 1) {
        for (let j = -r; j <= r; j += 1) {
          if (Math.max(Math.abs(i), Math.abs(j)) !== r) continue;
          const list = this.cells.get(this.key(cx + i, cz + j));
          if (!list) continue;
          for (const k of list) {
            const dx = this.x[k] - x;
            const dz = this.z[k] - z;
            const d = dx * dx + dz * dz;
            if (d < best) {
              best = d;
              bi = k;
            }
          }
        }
      }
      if (best < Infinity && (r - 1) * CELL > Math.sqrt(best)) break;
    }
    this.out.d = Math.sqrt(best);
    this.out.y = this.y[bi];
    this.out.s = this.s[bi];
    return this.out;
  }
}

export function createCanyon(track, materials, tier, seedWord) {
  const noise = new ImprovedNoise();
  const index = new TrackIndex(track);
  const salt = (hashString(seedWord) % 1000) * 0.37;

  const sample = { h: 0, t: 0, d: 0, ty: 0 };
  const heightAt = (x, z) => {
    const q = index.nearest(x, z);
    const n1 = noise.noise(x * 0.011, z * 0.011, salt);
    const n2 = noise.noise(x * 0.034, z * 0.034, salt + 4.2);
    const n3 = noise.noise(x * 0.09, z * 0.09, salt + 9.1);
    const ty = q.y;
    const d = q.d;
    let floor = ty - FLOOR + n2 * 1.3 + n3 * 0.5;
    floor -= (1 - smoothstep(2, 10, d)) * 2.4;
    const wallStart = 17 + n1 * 5;
    const wallWidth = 24 + n2 * 9;
    const t = Math.max(0, Math.min(1, (d - wallStart) / wallWidth));
    const steps = 4;
    const ts = t * steps;
    const fi = Math.floor(ts);
    const stepped = (fi + smoothstep(0, 1, ts - fi)) / steps;
    const cliff = t + (stepped - t) * 0.45;
    const rim = ty + 14 + (n1 * 0.5 + 0.5) * 30 + n2 * 5;
    let h = floor + (rim - floor) * cliff + n3 * 1.4 * t;
    const beyond = d - wallStart - wallWidth;
    if (beyond > 0) h += beyond * 0.06 * (n1 + 0.7) + Math.max(0, n2) * 6 * smoothstep(0, 30, beyond);
    sample.h = h;
    sample.t = t;
    sample.d = d;
    sample.ty = ty;
    return h;
  };

  // Which tiles to build: every tile within REACH of the track.
  const tiles = new Map();
  for (let i = 0; i < track.count; i += 12) {
    const x = track.px[i];
    const z = track.pz[i];
    for (let tx = Math.floor((x - REACH) / TILE); tx <= Math.floor((x + REACH) / TILE); tx += 1) {
      for (let tz = Math.floor((z - REACH) / TILE); tz <= Math.floor((z + REACH) / TILE); tz += 1) {
        const key = `${tx},${tz}`;
        if (tiles.has(key)) continue;
        const cxw = (tx + 0.5) * TILE;
        const czw = (tz + 0.5) * TILE;
        const q = index.nearest(cxw, czw);
        if (q.d > REACH + TILE * 0.5) continue;
        tiles.set(key, { tx, tz, s: q.s });
      }
    }
  }

  const step = tier.terrainStep;
  const res = Math.round(TILE / step);
  const buckets = new Map();
  for (const tile of tiles.values()) {
    const b = Math.floor((tile.s - track.first) / BUCKET);
    if (!buckets.has(b)) buckets.set(b, []);
    buckets.get(b).push(tile);
  }

  const group = new Group();
  const meshes = [];
  const ring = res + 3;
  const heights = new Float32Array(ring * ring);
  const ts = new Float32Array(ring * ring);
  const tys = new Float32Array(ring * ring);
  for (const [bucket, list] of buckets) {
    const verts = (res + 1) * (res + 1);
    const position = new Float32Array(list.length * verts * 3);
    const normal = new Float32Array(list.length * verts * 3);
    const color = new Float32Array(list.length * verts * 3);
    const uv = new Float32Array(list.length * verts * 2);
    const uv1 = new Float32Array(list.length * verts * 2);
    const indexArray = new Uint32Array(list.length * res * res * 6);
    let v = 0;
    let ii = 0;
    for (const tile of list) {
      const x0 = tile.tx * TILE;
      const z0 = tile.tz * TILE;
      // Heights on a grid one cell wider than the tile, so normals match across tile edges.
      for (let j = 0; j < ring; j += 1) {
        for (let i = 0; i < ring; i += 1) {
          heights[j * ring + i] = heightAt(x0 + (i - 1) * step, z0 + (j - 1) * step);
          ts[j * ring + i] = sample.t;
          tys[j * ring + i] = sample.ty;
        }
      }
      const base = v;
      for (let j = 0; j <= res; j += 1) {
        for (let i = 0; i <= res; i += 1) {
          const x = x0 + i * step;
          const z = z0 + j * step;
          const c = (j + 1) * ring + (i + 1);
          const h = heights[c];
          const t = ts[c];
          const dx = heights[c + 1] - heights[c - 1];
          const dz = heights[c + ring] - heights[c - ring];
          let nx = -dx;
          let ny = 2 * step;
          let nz = -dz;
          const len = Math.hypot(nx, ny, nz);
          nx /= len;
          ny /= len;
          nz /= len;
          const o = v * 3;
          position[o] = x;
          position[o + 1] = h;
          position[o + 2] = z;
          normal[o] = nx;
          normal[o + 1] = ny;
          normal[o + 2] = nz;
          // Light falls off toward the floor and into the creases at the foot of each terrace.
          const crease = 1 - Math.max(0, 0.35 - ny) * 0.6;
          const ao = (0.5 + 0.5 * smoothstep(0, 0.45, t)) * crease;
          color[o] = ao;
          color[o + 1] = ao;
          color[o + 2] = ao;
          const w = v * 2;
          uv[w] = x * 0.045 + z * 0.03;
          uv[w + 1] = h * 0.06 + (x - z) * 0.012;
          // Strata follow height up the walls; on the near-flat floor they follow the track's level instead, so
          // band edges run smooth rather than tracing the grid's triangles.
          const level = tys[c] - FLOOR + (h - tys[c] + FLOOR) * smoothstep(0.02, 0.3, t);
          uv1[w] = level * 0.0105 + noise.noise(x * 0.02, z * 0.02, salt + 2) * 0.035;
          uv1[w + 1] = 0.5;
          v += 1;
        }
      }
      for (let j = 0; j < res; j += 1) {
        for (let i = 0; i < res; i += 1) {
          const a = base + j * (res + 1) + i;
          const b = a + res + 1;
          indexArray[ii++] = a;
          indexArray[ii++] = b;
          indexArray[ii++] = a + 1;
          indexArray[ii++] = a + 1;
          indexArray[ii++] = b;
          indexArray[ii++] = b + 1;
        }
      }
    }
    const geometry = new BufferGeometry();
    geometry.setAttribute("position", new BufferAttribute(position, 3));
    geometry.setAttribute("normal", new BufferAttribute(normal, 3));
    geometry.setAttribute("color", new BufferAttribute(color, 3));
    geometry.setAttribute("uv", new BufferAttribute(uv, 2));
    geometry.setAttribute("uv1", new BufferAttribute(uv1, 2));
    geometry.setIndex(new BufferAttribute(indexArray, 1));
    geometry.computeBoundingSphere();
    const mesh = new Mesh(geometry, materials.rock);
    mesh.userData.bucket = bucket;
    mesh.receiveShadow = false;
    meshes.push(mesh);
    group.add(mesh);
  }

  // The river along the canyon floor, under the ribbon.
  const riverRows = [];
  for (let i = 0; i < track.count; i += 6) riverRows.push(i);
  const rp = new Float32Array(riverRows.length * 2 * 3);
  const rn = new Float32Array(riverRows.length * 2 * 3);
  const ru = new Float32Array(riverRows.length * 2 * 2);
  const ri = [];
  riverRows.forEach((i, k) => {
    const tx = track.tx[i];
    const tz = track.tz[i];
    const len = Math.hypot(tx, tz) || 1;
    const rx = -tz / len;
    const rz = tx / len;
    const y = track.py[i] - FLOOR - 0.9;
    for (let side = 0; side < 2; side += 1) {
      const sgn = side ? 1 : -1;
      const o = (k * 2 + side) * 3;
      rp[o] = track.px[i] - rx * 7 * sgn;
      rp[o + 1] = y;
      rp[o + 2] = track.pz[i] - rz * 7 * sgn;
      rn[o + 1] = 1;
      ru[(k * 2 + side) * 2] = side;
      ru[(k * 2 + side) * 2 + 1] = k * 0.2;
    }
    if (k > 0) {
      const a = (k - 1) * 2;
      ri.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
    }
  });
  const riverGeometry = new BufferGeometry();
  riverGeometry.setAttribute("position", new BufferAttribute(rp, 3));
  riverGeometry.setAttribute("normal", new BufferAttribute(rn, 3));
  riverGeometry.setAttribute("uv", new BufferAttribute(ru, 2));
  riverGeometry.setIndex(ri);
  riverGeometry.computeBoundingSphere();
  const river = new Mesh(riverGeometry, materials.river);
  group.add(river);

  // Boulders at the foot of the walls, hoodoos along the rims.
  const rng = createRng(hashString(`${seedWord}|rocks`));
  const boulderCount = Math.round(240 * tier.particles);
  const hoodooCount = Math.round(90 * tier.particles);
  const boulders = new InstancedMesh(new IcosahedronGeometry(1, 0), materials.boulder, boulderCount);
  const hoodooGeometry = mergeGeometries([
    { geometry: new CylinderGeometry(0.55, 1, 6, 7, 1), matrix: new Matrix4().makeTranslation(0, 3, 0) },
    { geometry: new CylinderGeometry(0.35, 0.6, 3, 7, 1), matrix: new Matrix4().makeTranslation(0, 7.4, 0) },
    { geometry: new IcosahedronGeometry(1.1, 0), matrix: new Matrix4().makeScale(1.3, 0.7, 1.3).setPosition(0, 9.3, 0) },
  ]);
  const hoodoos = new InstancedMesh(hoodooGeometry, materials.boulder, hoodooCount);
  // Each boulder's contact shadow: a soft patch laid on the slope under it.
  const shadows = new InstancedMesh(new PlaneGeometry(1, 1).rotateX(-Math.PI / 2), materials.rockShadow, boulderCount);
  const m = new Matrix4();
  const q = new Quaternion();
  const scale = new Vector3();
  const pos = new Vector3();
  const axis = new Vector3();
  const up = new Vector3(0, 1, 0);
  const slope = new Vector3();
  const tone = new Color();
  const place = (mesh, count, pick) => {
    let k = 0;
    let tries = 0;
    while (k < count && tries < count * 6) {
      tries += 1;
      const i = Math.floor(rng() * track.count);
      const tx = track.tx[i];
      const tz = track.tz[i];
      const len = Math.hypot(tx, tz) || 1;
      const side = rng() < 0.5 ? -1 : 1;
      const spot = pick();
      if (!spot) continue;
      const x = track.px[i] + (-tz / len) * spot.d * side;
      const z = track.pz[i] + (tx / len) * spot.d * side;
      const h = heightAt(x, z);
      if (sample.d < spot.min) continue;
      // The chase camera always rides the track, so a rock's size is held to its distance from the nearest
      // stretch of it: nothing ever comes close enough to fill an edge of the frame.
      const reach = Math.hypot(sample.d, h - sample.ty);
      const sz = Math.min(spot.size(), reach * spot.scaleLimit);
      const ys = spot.upright ? rng.range(0.8, 1.6) : rng.range(0.55, 0.8);
      scale.set(sz * rng.range(0.8, 1.3), sz * ys, sz * rng.range(0.8, 1.3));
      // Boulders sink well into the ground, so they meet it along a broad base rather than on a point.
      pos.set(x, h - (spot.upright ? spot.sink : sz * ys * 0.45), z);
      axis.set(rng() - 0.5, spot.upright ? 6 : rng() - 0.5, rng() - 0.5).normalize();
      q.setFromAxisAngle(axis, rng() * Math.PI * 2);
      m.compose(pos, q, scale);
      mesh.setMatrixAt(k, m);
      tone.copy(materials.palette[Math.floor(rng() * 5)]);
      tone.multiplyScalar(spot.upright ? 1 : 0.85);
      mesh.setColorAt(k, tone);
      if (!spot.upright) {
        const e = 0.6;
        slope.set(heightAt(x - e, z) - heightAt(x + e, z), 2 * e, heightAt(x, z - e) - heightAt(x, z + e)).normalize();
        q.setFromUnitVectors(up, slope);
        pos.set(x, h, z).addScaledVector(slope, 0.25);
        const r = sz * 3.2;
        m.compose(pos, q, scale.set(r, 1, r));
        shadows.setMatrixAt(k, m);
      }
      k += 1;
    }
    mesh.count = k;
    return k;
  };
  shadows.count = place(boulders, boulderCount, () => ({ d: rng.range(13, 40), min: 11, upright: false, scaleLimit: 0.045, size: () => rng.range(0.6, 2.8) }));
  place(hoodoos, hoodooCount, () => ({ d: rng.range(44, 80), min: 38, sink: 0.6, upright: true, scaleLimit: 0.05, size: () => rng.range(0.9, 2.1) }));
  boulders.receiveShadow = false;
  shadows.renderOrder = 1;
  group.add(shadows, boulders, hoodoos);

  return {
    group,
    meshes,
    river,
    heightAt,
    recolor() {
      // Rocks re-pick their tones from the palette when the scheme changes.
      const r2 = createRng(hashString(`${seedWord}|tones`));
      for (const mesh of [boulders, hoodoos]) {
        for (let i = 0; i < mesh.count; i += 1) {
          tone.copy(materials.palette[Math.floor(r2() * 5)]);
          mesh.setColorAt(i, tone);
        }
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      }
    },
  };
}
