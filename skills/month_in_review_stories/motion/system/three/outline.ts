// A glyph's filled regions as three shapes when one of its contours crosses itself, as a variable font's default
// instance draws an "r" or an "i" of Geist Mono: each contour is flattened to a polyline, cut at every point where it
// crosses itself into simple loops, and every loop is filled or left open by the font's nonzero rule, an open loop
// becoming a hole of the smallest filled loop around it. A glyph whose contours are all simple returns null.
import * as THREE from 'three';

type P = [number, number];

/** Where segments a-b and c-d cross, as the share along each, or null when they do not. */
const cross = (a: P, b: P, c: P, d: P): [number, number] | null => {
  const r: P = [b[0] - a[0], b[1] - a[1]];
  const s: P = [d[0] - c[0], d[1] - c[1]];
  const den = r[0] * s[1] - r[1] * s[0];
  if (Math.abs(den) < 1e-12) return null;
  const q: P = [c[0] - a[0], c[1] - a[1]];
  const t = (q[0] * s[1] - q[1] * s[0]) / den;
  const u = (q[0] * r[1] - q[1] * r[0]) / den;
  return t > 1e-9 && t < 1 - 1e-9 && u > 1e-9 && u < 1 - 1e-9 ? [t, u] : null;
};

/** The contour's points with every self-crossing put in at its place along both segments, each crossing as one key. */
const withCrossings = (pts: P[]) => {
  const n = pts.length;
  const at: {t: number; key: number; p: P}[][] = pts.map(() => []);
  let key = 0;
  for (let i = 0; i < n; i++) {
    for (let j = i + 2; j < n; j++) {
      if (i === 0 && j === n - 1) continue;
      const x = cross(pts[i], pts[(i + 1) % n], pts[j], pts[(j + 1) % n]);
      if (!x) continue;
      const p: P = [pts[i][0] + x[0] * (pts[(i + 1) % n][0] - pts[i][0]), pts[i][1] + x[0] * (pts[(i + 1) % n][1] - pts[i][1])];
      at[i].push({t: x[0], key, p});
      at[j].push({t: x[1], key, p});
      key++;
    }
  }
  if (!key) return null;
  const out: {p: P; key: number}[] = [];
  pts.forEach((p, i) => {
    out.push({p, key: -1});
    at[i].sort((a, b) => a.t - b.t).forEach((x) => out.push({p: x.p, key: x.key}));
  });
  return out;
};

/** The simple loops a self-crossing contour is made of: each time the walk comes back to a crossing it has passed,
 * the stretch since then closes into a loop and the walk goes on from the crossing. */
const loopsOf = (seq: {p: P; key: number}[]) => {
  const loops: P[][] = [];
  const stack: {p: P; key: number}[] = [];
  for (const v of seq) {
    const k = v.key < 0 ? -1 : stack.findIndex((w) => w.key === v.key);
    if (k >= 0) {
      loops.push(stack.splice(k + 1).map((w) => w.p).concat([stack[k].p]));
    } else stack.push(v);
  }
  loops.push(stack.map((w) => w.p));
  return loops.filter((l) => l.length >= 3 && Math.abs(area(l)) > 1e-7);
};

const area = (l: P[]) => l.reduce((a, p, i) => a + p[0] * l[(i + 1) % l.length][1] - l[(i + 1) % l.length][0] * p[1], 0) / 2;

/** How many times the contours wind around point `q`, signed. */
const winding = (q: P, contours: P[][]) => {
  let w = 0;
  for (const c of contours) {
    for (let i = 0; i < c.length; i++) {
      const a = c[i];
      const b = c[(i + 1) % c.length];
      const side = (b[0] - a[0]) * (q[1] - a[1]) - (q[0] - a[0]) * (b[1] - a[1]);
      if (a[1] <= q[1] && b[1] > q[1] && side > 0) w++;
      else if (a[1] > q[1] && b[1] <= q[1] && side < 0) w--;
    }
  }
  return w;
};

/** A point just inside a simple loop: off the middle of its longest edge, on the loop's inner side. */
const inside = (l: P[]): P => {
  let k = 0;
  let best = -1;
  l.forEach((p, i) => {
    const b = l[(i + 1) % l.length];
    const d = Math.hypot(b[0] - p[0], b[1] - p[1]);
    if (d > best) [best, k] = [d, i];
  });
  const a = l[k];
  const b = l[(k + 1) % l.length];
  const turn = area(l) > 0 ? 1 : -1;
  const e = 1e-4 / best;
  return [(a[0] + b[0]) / 2 - turn * (b[1] - a[1]) * e, (a[1] + b[1]) / 2 + turn * (b[0] - a[0]) * e];
};

const contains = (l: P[], q: P) => winding(q, [l]) !== 0;

/** The glyph path's filled shapes by the nonzero rule, or null when no contour crosses itself. */
export const resolvedShapes = (path: THREE.ShapePath, divisions = 8): THREE.Shape[] | null => {
  const contours = path.subPaths.map((sp) => {
    const pts = sp.getPoints(divisions).map((v) => [v.x, v.y] as P);
    const [a, z] = [pts[0], pts[pts.length - 1]];
    if (pts.length > 1 && Math.hypot(a[0] - z[0], a[1] - z[1]) < 1e-9) pts.pop();
    return pts;
  });
  const split = contours.map(withCrossings);
  if (split.every((s) => s === null)) return null;
  const loops = contours.flatMap((c, i) => (split[i] ? loopsOf(split[i]!) : [c]));
  const filled = loops.filter((l) => winding(inside(l), contours) !== 0);
  const open = loops.filter((l) => !filled.includes(l));
  const shapes = filled.map((l) => new THREE.Shape(l.map(([x, y]) => new THREE.Vector2(x, y))));
  open.forEach((l) => {
    const q = inside(l);
    let k = -1;
    filled.forEach((f, i) => {
      if (contains(f, q) && (k < 0 || Math.abs(area(f)) < Math.abs(area(filled[k])))) k = i;
    });
    if (k >= 0) shapes[k].holes.push(new THREE.Path(l.map(([x, y]) => new THREE.Vector2(x, y))));
  });
  return shapes;
};
