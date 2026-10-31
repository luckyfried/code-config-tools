// Motion as pure functions of time: every value a film in the camera's space shows is computed from the frame, so
// any frame renders alone and nothing accumulates between frames.

export type Vec3 = [number, number, number];
export type Pt = [number, number];

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
export const mixPt = (a: Pt, b: Pt, t: number): Pt => [lerp(a[0], b[0], t), lerp(a[1], b[1], t)];
export const mix3 = (a: Vec3, b: Vec3, t: number): Vec3 => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)];
export const smooth = (t: number) => {
  const u = clamp01(t);
  return u * u * (3 - 2 * u);
};

/** The CSS cubic-bezier curve [x1, y1, x2, y2] as a function of progress, solved by Newton steps then bisection. */
export const bezier = ([x1, y1, x2, y2]: number[]) => {
  const ax = 3 * x1 - 3 * x2 + 1, bx = 3 * x2 - 6 * x1, cx = 3 * x1;
  const ay = 3 * y1 - 3 * y2 + 1, by = 3 * y2 - 6 * y1, cy = 3 * y1;
  const x = (t: number) => ((ax * t + bx) * t + cx) * t;
  const y = (t: number) => ((ay * t + by) * t + cy) * t;
  const dx = (t: number) => (3 * ax * t + 2 * bx) * t + cx;
  return (p: number) => {
    if (p <= 0) return 0;
    if (p >= 1) return 1;
    let t = p;
    for (let i = 0; i < 6; i++) {
      const e = x(t) - p;
      const d = dx(t);
      if (Math.abs(e) < 1e-6) return y(t);
      if (Math.abs(d) < 1e-6) break;
      t -= e / d;
    }
    let lo = 0, hi = 1;
    t = p;
    for (let i = 0; i < 30; i++) {
      if (x(t) < p) lo = t;
      else hi = t;
      t = (lo + hi) / 2;
    }
    return y(t);
  };
};

/** Progress 0 to 1 of `t` through [a, a + len], clamped, through `curve`. */
export const span = (t: number, a: number, len: number, curve: (u: number) => number = smooth) => curve(clamp01((t - a) / Math.max(1e-6, len)));

/** Deterministic hash noise in [-1, 1]. */
export const hash = (n: number) => {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return (s - Math.floor(s)) * 2 - 1;
};

/** Smooth value noise in [-1, 1] for a continuous time `t`. */
export const smoothNoise = (t: number, seed: number) => {
  const i = Math.floor(t);
  const f = t - i;
  const u = f * f * (3 - 2 * f);
  return lerp(hash(i + seed * 57.3), hash(i + 1 + seed * 57.3), u);
};

/** A damped ring after an event at `start`: 0 before it, a decaying sine after, `period` and `decay` in the same units. */
export const ring = (t: number, start: number, period: number, decay: number) =>
  t < start ? 0 : Math.sin(((t - start) / period) * Math.PI * 2) * Math.exp(-(t - start) / decay);
