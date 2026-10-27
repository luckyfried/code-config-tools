// The camera: which time sits at the start of the time axis (`t0`, ms) and how many milliseconds one pixel covers
// (`k`). Pure functions, so a recorded gesture replays the same way in a test as on a phone.

export const timeAt = (cam, px) => cam.t0 + px * cam.k;
export const pxOf = (cam, t) => (t - cam.t0) / cam.k;

/** The camera that shows `from` at pixel `a` and `to` at pixel `b`. */
export const fit = (from, to, a, b) => {
  const k = (to - from) / Math.max(1, b - a);
  return { t0: from - a * k, k };
};

/** Zoom by `factor` (2 is twice as close) keeping the time under pixel `px` where it is. */
export function zoomAt(cam, px, factor) {
  const t = timeAt(cam, px);
  const k = cam.k / factor;
  return { t0: t - px * k, k };
}

/** Pan by `dpx` pixels along the time axis (positive moves the content forward, as a drag does). */
export const panBy = (cam, dpx) => ({ t0: cam.t0 - dpx * cam.k, k: cam.k });

/**
 * Keeps the camera inside `limits`: `kMin` and `kMax` bound the zoom, and the time at the middle of the axis
 * (`length` pixels long) stays between `tMin` and `tMax`.
 */
export function clampCamera(cam, { kMin, kMax, tMin, tMax, length }) {
  const k = Math.min(kMax, Math.max(kMin, cam.k));
  const middle = cam.t0 + (length / 2) * cam.k;
  const kept = Math.min(tMax, Math.max(tMin, middle));
  return { t0: kept - (length / 2) * k, k };
}

const distance = (a, b) => Math.hypot(a.x - b.x, a.y - b.y);

/**
 * A pinch: two pointers that started at `start.a` and `start.b` with the camera `start.cam` are now at `a` and `b`.
 * The zoom is the ratio of the two-pointer distances, and the time that was under the starting midpoint stays under
 * the midpoint now, so the timeline follows both fingers. `axis` is "x" or "y", whichever runs along time.
 */
export function pinch(start, a, b, axis) {
  const d0 = Math.max(8, distance(start.a, start.b));
  const d1 = Math.max(8, distance(a, b));
  const m0 = (start.a[axis] + start.b[axis]) / 2;
  const m1 = (a[axis] + b[axis]) / 2;
  const t = timeAt(start.cam, m0);
  const k = start.cam.k * (d0 / d1);
  return { t0: t - m1 * k, k };
}

/**
 * The smooth zoom-and-pan path between two cameras (van Wijk and Nuij): far moves pull back so the eye keeps its
 * place, then settle in. Returns `at(s)` for s from 0 to 1. `length` is the time axis in pixels.
 */
export function flight(from, to, length, rho = 1.2) {
  const w0 = from.k * length;
  const w1 = to.k * length;
  const c0 = from.t0 + w0 / 2;
  const c1 = to.t0 + w1 / 2;
  // Worked in units of the starting width, so years and days are both well inside a double's precision.
  const dx = (c1 - c0) / w0;
  const ratio = w1 / w0;
  const rho2 = rho * rho;
  const rho4 = rho2 * rho2;
  const camera = (center, width) => ({ t0: c0 + center * w0 - (width * w0) / 2, k: (width * w0) / length });
  if (Math.abs(dx) < 1e-9) {
    const S = Math.log(ratio) / rho;
    return (s) => camera(s * dx, Math.exp(rho * s * S));
  }
  const d1 = Math.abs(dx);
  const b0 = (ratio * ratio - 1 + rho4 * d1 * d1) / (2 * rho2 * d1);
  const b1 = (ratio * ratio - 1 - rho4 * d1 * d1) / (2 * ratio * rho2 * d1);
  const r0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0);
  const r1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1);
  const S = (r1 - r0) / rho;
  return (s) => {
    if (s >= 1) return { ...to };
    const at = s * S;
    const u = (1 / (rho2 * d1)) * (Math.cosh(r0) * Math.tanh(rho * at + r0) - Math.sinh(r0));
    return camera(u * dx, Math.cosh(r0) / Math.cosh(rho * at + r0));
  };
}
