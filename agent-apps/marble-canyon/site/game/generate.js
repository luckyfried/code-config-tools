// The canyon track from a seed: a downhill random walk in heading with a bounded turn rate and a monotone drop,
// so the spline never crosses itself; then an arc-length table of banked frames, and the features placed by
// arc length (three gates, the jumps, the boost pads).
import { CatmullRomCurve3, Vector3 } from "three";
import { createRng, hashString } from "./rng.js";

export const LENGTHS = { short: 1150, medium: 2000, long: 3150 };
export const HALF_WIDTH = 3.0;
export const MARBLE_RADIUS = 0.8;
export const DISH = 0.45;
export const KERB = 0.9;
export const GRAVITY = 30;
export const BANK_SPEED = 30;
export const MAX_ROLL = 0.55;
export const GAP_LENGTH = 15;
export const GAP_STEP = 1.4;
export const KICKER = 9;
export const PAD_LENGTH = 9;
export const PAD_HALF = 0.26;
export const START_PAD = 40;
export const END_PAD = 90;

const STEP = 22;
const MAX_HEADING = 1.15;
const UP = new Vector3(0, 1, 0);

const smooth = (values, radius) => {
  const out = new Float32Array(values.length);
  const n = values.length;
  let sum = 0;
  let count = 0;
  for (let i = -radius; i <= radius; i += 1) {
    if (i >= 0 && i < n) {
      sum += values[i];
      count += 1;
    }
  }
  for (let i = 0; i < n; i += 1) {
    out[i] = sum / count;
    const drop = i - radius;
    const add = i + radius + 1;
    if (drop >= 0) {
      sum -= values[drop];
      count -= 1;
    }
    if (add < n) {
      sum += values[add];
      count += 1;
    }
  }
  return out;
};

export function generateTrack(seedWord, lengthName) {
  const length = LENGTHS[lengthName] ?? LENGTHS.medium;
  const rng = createRng(hashString(`${String(seedWord).toLowerCase()}|${lengthName}`));

  // Control points: heading walks toward a fresh target turn every few steps, held inside ±MAX_HEADING of
  // straight downhill, so every point is further along -z than the last and the ribbon cannot cross itself.
  const points = [];
  let x = 0;
  let y = 0;
  let z = 0;
  let heading = 0;
  let turn = 0;
  let targetTurn = 0;
  let grade = 0.11;
  let targetGrade = 0.11;
  let hold = 0;
  const total = length + START_PAD + END_PAD;
  const count = Math.ceil((total * 1.05) / STEP) + 6;
  points.push(new Vector3(x, y, z));
  for (let i = 1; i < count; i += 1) {
    if (i < 4 || i > count - 6) {
      targetTurn = 0;
    } else if (hold <= 0) {
      const straight = rng() < 0.18;
      targetTurn = straight ? 0 : rng.range(0.1, 0.34) * (rng() < 0.5 ? -1 : 1);
      if (Math.abs(heading) > MAX_HEADING * 0.6 && Math.sign(targetTurn) === Math.sign(heading)) targetTurn *= -1;
      hold = 2 + Math.floor(rng() * 4);
      targetGrade = rng.range(0.07, 0.15);
    }
    hold -= 1;
    turn += (targetTurn - turn) * 0.5;
    heading += turn;
    if (Math.abs(heading) > MAX_HEADING) {
      heading = Math.sign(heading) * MAX_HEADING;
      turn = 0;
      targetTurn = -targetTurn * 0.5;
    }
    grade += (targetGrade - grade) * 0.35;
    const g = i < 4 ? 0.16 : grade;
    x += Math.sin(heading) * STEP;
    z -= Math.cos(heading) * STEP;
    y -= STEP * g;
    points.push(new Vector3(x, y, z));
  }
  // Every canyon drops the same height per unit of length, so one length gives one fair set of medal times.
  const drop = -points[points.length - 1].y;
  const want = (points.length - 1) * STEP * 0.11;
  for (const point of points) point.y *= want / drop;

  const curve = new CatmullRomCurve3(points, false, "centripetal");
  curve.arcLengthDivisions = points.length * 24;
  const curveLength = curve.getLength();
  const first = -START_PAD;
  const last = length + END_PAD;
  const n = Math.floor(last - first) + 1;
  const offset = Math.max(0, (curveLength - (last - first)) * 0.5);

  const px = new Float32Array(n);
  const py = new Float32Array(n);
  const pz = new Float32Array(n);
  const tx = new Float32Array(n);
  const ty = new Float32Array(n);
  const tz = new Float32Array(n);
  const headingAt = new Float32Array(n);
  const p = new Vector3();
  const t = new Vector3();
  for (let i = 0; i < n; i += 1) {
    const u = Math.min(1, (offset + i) / curveLength);
    curve.getPointAt(u, p);
    curve.getTangentAt(u, t);
    px[i] = p.x;
    py[i] = p.y;
    pz[i] = p.z;
    tx[i] = t.x;
    ty[i] = t.y;
    tz[i] = t.z;
    headingAt[i] = Math.atan2(t.x, -t.z);
  }
  const x0 = px[START_PAD];
  const y0 = py[START_PAD];
  const z0 = pz[START_PAD];
  for (let i = 0; i < n; i += 1) {
    px[i] -= x0;
    py[i] -= y0;
    pz[i] -= z0;
  }

  // Signed curvature (positive turns right), smoothed, then the bank that balances it at BANK_SPEED, eased in.
  const rawCurve = new Float32Array(n);
  for (let i = 1; i < n - 1; i += 1) {
    let d = headingAt[i + 1] - headingAt[i - 1];
    if (d > Math.PI) d -= Math.PI * 2;
    if (d < -Math.PI) d += Math.PI * 2;
    rawCurve[i] = d / 2;
  }
  const curvature = smooth(rawCurve, 4);
  const rawRoll = new Float32Array(n);
  for (let i = 0; i < n; i += 1) {
    const want = -Math.atan((BANK_SPEED * BANK_SPEED * curvature[i]) / GRAVITY) * 0.85;
    rawRoll[i] = Math.max(-MAX_ROLL, Math.min(MAX_ROLL, want));
  }
  const roll = smooth(smooth(rawRoll, 14), 10);

  // Features by arc length (s = 0 is the start line).
  const index = (s) => Math.max(0, Math.min(n - 1, Math.round(s - first)));
  const windowCurve = (s, r) => {
    let m = 0;
    for (let k = index(s - r); k <= index(s + r); k += 1) m = Math.max(m, Math.abs(curvature[k]));
    return m;
  };
  const gates = [0.25, 0.5, 0.75].map((f) => ({ s: Math.round(length * f) }));
  const jumpCount = length < 1500 ? 2 : length < 2600 ? 3 : 4;
  const gaps = [];
  for (let j = 0; j < jumpCount; j += 1) {
    const lo = 160 + ((length - 280) * j) / jumpCount;
    const hi = 160 + ((length - 280) * (j + 1)) / jumpCount - 40;
    let best = null;
    let bestScore = Infinity;
    for (let s = lo; s <= hi; s += 5) {
      const nearGate = gates.some((gate) => Math.abs(gate.s - s) < 70 || Math.abs(gate.s - (s + GAP_LENGTH)) < 70);
      if (nearGate) continue;
      const score = windowCurve(s + GAP_LENGTH * 0.5, 34) + rng() * 0.004;
      if (score < bestScore) {
        bestScore = score;
        best = s;
      }
    }
    if (best !== null) gaps.push({ s0: best, s1: best + GAP_LENGTH });
  }

  // Landing sides sit GAP_STEP lower than the lip, and the last KICKER units before a gap rise into a ramp.
  const kick = new Float32Array(n);
  for (const gap of gaps) {
    const mid = gap.s0 + GAP_LENGTH * 0.5;
    for (let i = 0; i < n; i += 1) {
      const s = first + i;
      if (s > mid) py[i] -= GAP_STEP;
      const k = (s - (gap.s0 - KICKER)) / KICKER;
      if (k > 0 && k <= 1) kick[i] = Math.max(kick[i], k * k * (3 - 2 * k));
    }
  }
  for (let i = 0; i < n; i += 1) py[i] += kick[i] * 0.7;

  const boosts = [];
  const lanes = [-0.5, 0, 0.5];
  const clear = (s) =>
    gaps.every((gap) => s + PAD_LENGTH < gap.s0 - KICKER - 6 || s > gap.s1 + 30) &&
    gates.every((gate) => Math.abs(gate.s - s) > 18) &&
    boosts.every((b) => Math.abs(b.s - s) > 60);
  for (const gap of gaps) {
    const s = gap.s0 - 75;
    if (clear(s)) boosts.push({ s, c: rng.pick(lanes) });
  }
  const padCount = Math.round(length / 170);
  for (let k = 0; k < padCount; k += 1) {
    const s = Math.round(110 + (k * (length - 180)) / padCount + rng.range(-25, 25));
    if (clear(s)) boosts.push({ s, c: rng.pick(lanes) });
  }
  boosts.sort((a, b) => a.s - b.s);

  // Banked frames: the tangent, a right vector level with the world, and the up vector; then the roll about the
  // tangent. Anchoring the transported frame to world up keeps the ribbon from twisting through bank changes.
  const rx = new Float32Array(n);
  const ry = new Float32Array(n);
  const rz = new Float32Array(n);
  const nx = new Float32Array(n);
  const ny = new Float32Array(n);
  const nz = new Float32Array(n);
  const T = new Vector3();
  const R = new Vector3();
  const N = new Vector3();
  for (let i = 0; i < n; i += 1) {
    T.set(tx[i], ty[i], tz[i]).normalize();
    R.crossVectors(T, UP).normalize();
    N.crossVectors(R, T).normalize();
    const c = Math.cos(roll[i]);
    const s = Math.sin(roll[i]);
    rx[i] = R.x * c + N.x * s;
    ry[i] = R.y * c + N.y * s;
    rz[i] = R.z * c + N.z * s;
    nx[i] = N.x * c - R.x * s;
    ny[i] = N.y * c - R.y * s;
    nz[i] = N.z * c - R.z * s;
  }

  return {
    seed: String(seedWord),
    lengthName,
    length,
    first,
    last,
    count: n,
    px,
    py,
    pz,
    tx,
    ty,
    tz,
    rx,
    ry,
    rz,
    nx,
    ny,
    nz,
    roll,
    curvature,
    kick,
    gates,
    gaps,
    boosts,
  };
}

// Interpolated frame at arc length s into a plain object { p, t, r, n, roll, curvature } of arrays.
export function frameAt(track, s, out) {
  const f = Math.max(0, Math.min(track.count - 1.0001, s - track.first));
  const i = Math.floor(f);
  const k = f - i;
  const j = i + 1;
  const lerp = (a) => a[i] + (a[j] - a[i]) * k;
  out.p[0] = lerp(track.px);
  out.p[1] = lerp(track.py);
  out.p[2] = lerp(track.pz);
  out.t[0] = lerp(track.tx);
  out.t[1] = lerp(track.ty);
  out.t[2] = lerp(track.tz);
  out.r[0] = lerp(track.rx);
  out.r[1] = lerp(track.ry);
  out.r[2] = lerp(track.rz);
  out.n[0] = lerp(track.nx);
  out.n[1] = lerp(track.ny);
  out.n[2] = lerp(track.nz);
  out.roll = lerp(track.roll);
  out.curvature = lerp(track.curvature);
  return out;
}

export const newFrame = () => ({ p: [0, 0, 0], t: [0, 0, -1], r: [1, 0, 0], n: [0, 1, 0], roll: 0, curvature: 0 });

// Height of the dished surface across the track: a shallow channel that rises into the kerbs.
export function surfaceHeight(u) {
  const a = Math.abs(u);
  const kerb = a > KERB ? ((a - KERB) / (1 - KERB)) * 0.28 : 0;
  return DISH * u * u + kerb;
}

// Medal times from the track's length: the pace a clean run holds through the canyon, then looser bands.
export function medalTimes(track) {
  const gold = track.length / (26 + track.length / 700);
  return { gold, silver: gold * 1.1, bronze: gold * 1.25 };
}
