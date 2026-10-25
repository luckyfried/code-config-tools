// The planet from a seed word: one height function that both the mesh and the walk read, the biome at a point,
// the start, and where the crystals hide. Everything here is deterministic for a given seed.
import { SimplexNoise } from "three/addons/math/SimplexNoise.js";

export const RADIUS = 20;
export const SEA_LEVEL = 0;
export const WADE_DEPTH = -0.42;

export function hashSeed(word) {
  let h1 = 0xdeadbeef ^ word.length;
  let h2 = 0x41c6ce57 ^ word.length;
  for (let i = 0; i < word.length; i++) {
    const ch = word.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (h2 >>> 0) ^ (h1 >>> 0);
}

export function createRandom(seed) {
  let a = seed >>> 0;
  return function random() {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const smoothstep = (a, b, x) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

export function createTerrain(seedWord, { landBias = 0.05, snowline = 3.6 } = {}) {
  const random = createRandom(hashSeed(seedWord));
  const simplex = new SimplexNoise({ random });
  const o = Array.from({ length: 12 }, () => random() * 200 - 100);

  function fbm(x, y, z, octaves, ox, oy, oz) {
    let amp = 1;
    let freq = 1;
    let sum = 0;
    let norm = 0;
    for (let i = 0; i < octaves; i++) {
      sum += amp * simplex.noise3d(x * freq + ox, y * freq + oy, z * freq + oz);
      norm += amp;
      amp *= 0.5;
      freq *= 2.03;
    }
    return sum / norm;
  }

  // Continents first, then hills, then ridged mountains that only rise well inland.
  function land(x, y, z) {
    return fbm(x * 1.25, y * 1.25, z * 1.25, 5, o[0], o[1], o[2]) + landBias;
  }

  function height(x, y, z) {
    const c = land(x, y, z);
    if (c < 0) return Math.max(-3.2, c * 7.5);
    const hills = fbm(x * 3.4, y * 3.4, z * 3.4, 3, o[3], o[4], o[5]) * 0.5 + 0.5;
    const r = 1 - Math.abs(simplex.noise3d(x * 2.6 + o[6], y * 2.6 + o[7], z * 2.6 + o[8]));
    const ridge = r * r * r;
    const inland = smoothstep(0.02, 0.3, c);
    const mountain = smoothstep(0.12, 0.42, c);
    return c * 1.7 + inland * (hills * 0.7 + ridge * mountain * 3.1);
  }

  function moisture(x, y, z) {
    return fbm(x * 2.1, y * 2.1, z * 2.1, 2, o[9], o[10], o[11]);
  }

  // Biome by height, slope (1 is flat, 0 is a cliff), and moisture.
  function biome(h, flatness, wet) {
    if (h < -0.08) return "floor";
    if (h < 0.28) return "shore";
    if (h > snowline + (wet - 0.1) * 0.6) return "snow";
    if (flatness < 0.8 || h > snowline - 1.1) return "rock";
    if (wet > 0.04 && h < snowline - 1.3) return "forest";
    return "meadow";
  }

  // Ground normal at a direction, from finite differences of the height on the tangent plane.
  function groundNormal(dir, out) {
    const e = 0.012;
    const ax = Math.abs(dir.x) < 0.9 ? 1 : 0;
    const ay = ax ? 0 : 1;
    // tangent t1 = normalize(cross(dir, axis)), t2 = cross(dir, t1)
    let t1x = dir.y * 0 - dir.z * ay;
    let t1y = dir.z * ax - dir.x * 0;
    let t1z = dir.x * ay - dir.y * ax;
    const l1 = Math.hypot(t1x, t1y, t1z);
    t1x /= l1; t1y /= l1; t1z /= l1;
    const t2x = dir.y * t1z - dir.z * t1y;
    const t2y = dir.z * t1x - dir.x * t1z;
    const t2z = dir.x * t1y - dir.y * t1x;
    const s = (dx, dy, dz) => {
      const l = Math.hypot(dx, dy, dz);
      return Math.max(height(dx / l, dy / l, dz / l), WADE_DEPTH);
    };
    const h0 = s(dir.x, dir.y, dir.z);
    const h1 = s(dir.x + t1x * e, dir.y + t1y * e, dir.z + t1z * e);
    const h2 = s(dir.x + t2x * e, dir.y + t2y * e, dir.z + t2z * e);
    const step = e * (RADIUS + h0);
    const g1 = (h1 - h0) / step;
    const g2 = (h2 - h0) / step;
    out.set(dir.x - t1x * g1 - t2x * g2, dir.y - t1y * g1 - t2y * g2, dir.z - t1z * g1 - t2z * g2).normalize();
    return out;
  }

  return { random, height, moisture, biome, groundNormal, snowline, land };
}

function randomDir(random) {
  const u = random() * 2 - 1;
  const t = random() * Math.PI * 2;
  const s = Math.sqrt(1 - u * u);
  return [s * Math.cos(t), u, s * Math.sin(t)];
}

const angle = (a, b) => Math.acos(Math.min(1, Math.max(-1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2])));

// A meadow start near the coast of a continent, so the first view shows land, sea, and a beam.
export function pickStart(terrain) {
  const random = createRandom(Math.floor(terrain.random() * 4294967296));
  let best = null;
  let bestScore = -Infinity;
  for (let i = 0; i < 400; i++) {
    const d = randomDir(random);
    const h = terrain.height(d[0], d[1], d[2]);
    if (h < 0.35 || h > 1.6) continue;
    const score = -Math.abs(h - 0.8) + random() * 0.4;
    if (score > bestScore) {
      bestScore = score;
      best = d;
    }
  }
  return best ?? [0, 1, 0];
}

// Crystals spread across the land by farthest-point picking: the first sits in view of the start (its beam is the
// first thing to walk toward), one sits on the far side behind the horizon, and the rest fill the gaps between.
export function placeCrystals(terrain, start, count) {
  const random = createRandom(Math.floor(terrain.random() * 4294967296));
  const candidates = [];
  for (let i = 0; i < 3000 && candidates.length < 900; i++) {
    const d = randomDir(random);
    const h = terrain.height(d[0], d[1], d[2]);
    if (h > 0.3 && h < terrain.snowline + 0.4) candidates.push(d);
  }
  const chosen = [];
  const near = candidates
    .filter((d) => {
      const a = angle(d, start);
      return a > 0.45 && a < 0.8;
    })
    .sort((a, b) => angle(a, start) - angle(b, start));
  if (near.length) chosen.push(near[Math.floor(near.length / 2)]);
  const far = candidates.filter((d) => angle(d, start) > 2.1);
  if (far.length && count > 1) chosen.push(far[Math.floor(random() * far.length)]);
  while (chosen.length < count && candidates.length) {
    let best = null;
    let bestDist = -1;
    for (const c of candidates) {
      let m = angle(c, start) * 0.6;
      for (const p of chosen) m = Math.min(m, angle(c, p));
      if (m > bestDist) {
        bestDist = m;
        best = c;
      }
    }
    if (!best) break;
    chosen.push(best);
  }
  return chosen.slice(0, count);
}
