// A variable TrueType font set at one instance: each glyph's outline and advance moved by the file's glyph variations
// (`gvar`) to the axis values a line names, the way a rasterizer sets them: user values normalized by `fvar`, remapped
// by `avar`, every point moved by the deltas of each region it falls in, the points a region leaves out inferred from
// their neighbours on the contour. A static file, or a file at its default instance, is the parsed font itself.

/** A parsed font as opentype.js gives it, with only what an instance reads. */
type Base = {
  unitsPerEm: number;
  tables: {fvar?: {axes: {tag: string; minValue: number; defaultValue: number; maxValue: number}[]}};
  charToGlyph: (c: string) => any;
  stringToGlyphs: (s: string) => any[];
  getKerningValue: (a: any, b: any) => number;
};

type Point = {x: number; y: number; onCurve: boolean; lastPointOfContour: boolean};
type Component = {glyphIndex: number; dx: number; dy: number; xScale: number; scale01: number; scale10: number; yScale: number; matchedPoints?: [number, number]};
export type Cmd = {type: string; x?: number; y?: number; x1?: number; y1?: number; x2?: number; y2?: number};

/** Axis values in the font's own units, by axis tag: {wght: 700}. An axis left out stays at its default. */
export type Coords = Record<string, number>;

/** Where each table starts in the file, by tag. */
const tablesOf = (v: DataView) => {
  const out: Record<string, number> = {};
  const n = v.getUint16(4);
  for (let i = 0; i < n; i++) {
    const at = 12 + 16 * i;
    out[String.fromCharCode(v.getUint8(at), v.getUint8(at + 1), v.getUint8(at + 2), v.getUint8(at + 3))] = v.getUint32(at + 8);
  }
  return out;
};

const f2dot14 = (v: DataView, at: number) => v.getInt16(at) / 16384;

/** `avar`'s map for each axis: [from, to] pairs in normalized coordinates, ascending. */
const avarOf = (v: DataView, at: number | undefined, axes: number): [number, number][][] => {
  if (at === undefined) return [];
  const maps: [number, number][][] = [];
  let p = at + 8;
  for (let a = 0; a < Math.min(axes, v.getUint16(at + 6)); a++) {
    const n = v.getUint16(p);
    p += 2;
    const m: [number, number][] = [];
    for (let k = 0; k < n; k++, p += 4) m.push([f2dot14(v, p), f2dot14(v, p + 2)]);
    maps.push(m);
  }
  return maps;
};

/** A user value normalized to -1..1 about the axis default, then through the axis's `avar` map. */
const normalize = (value: number, axis: {minValue: number; defaultValue: number; maxValue: number}, map?: [number, number][]) => {
  const x = Math.min(axis.maxValue, Math.max(axis.minValue, value));
  let n = x < axis.defaultValue ? (x - axis.defaultValue) / (axis.defaultValue - axis.minValue)
    : x > axis.defaultValue ? (x - axis.defaultValue) / (axis.maxValue - axis.defaultValue) : 0;
  if (map && map.length) {
    const k = map.findIndex(([from]) => from >= n);
    if (k <= 0) n = k === 0 ? map[0][1] : map[map.length - 1][1];
    else {
      const [a, b] = [map[k - 1], map[k]];
      n = b[0] === a[0] ? b[1] : a[1] + ((n - a[0]) * (b[1] - a[1])) / (b[0] - a[0]);
    }
  }
  return n;
};

/** How much of a region's deltas apply at `coords`: its peak, and its start and end when it names them. */
const scalarOf = (coords: number[], peak: number[], start?: number[], end?: number[]) => {
  let s = 1;
  for (let i = 0; i < coords.length; i++) {
    const p = peak[i], c = coords[i];
    if (p === 0 || c === p) continue;
    if (c === 0) return 0;
    if (start && end) {
      const a = start[i], b = end[i];
      if (a > p || p > b || (a < 0 && b > 0)) continue;
      if (c < a || c > b) return 0;
      s *= c < p ? (c - a) / (p - a) : (b - c) / (b - p);
    } else {
      if (c < Math.min(0, p) || c > Math.max(0, p)) return 0;
      s *= c / p;
    }
  }
  return s;
};

/** Packed point numbers at `at`: the numbers, or null for every point, and where the data after them starts. */
const pointsAt = (v: DataView, at: number): [number[] | null, number] => {
  let n = v.getUint8(at++);
  if (n === 0) return [null, at];
  if (n & 0x80) n = ((n & 0x7f) << 8) | v.getUint8(at++);
  const out: number[] = [];
  let last = 0;
  while (out.length < n) {
    const run = v.getUint8(at++);
    const words = run & 0x80;
    for (let k = 0; k < (run & 0x7f) + 1 && out.length < n; k++) {
      last += words ? v.getUint16(at) : v.getUint8(at);
      at += words ? 2 : 1;
      out.push(last);
    }
  }
  return [out, at];
};

/** `n` packed deltas at `at`, and where the data after them starts. */
const deltasAt = (v: DataView, at: number, n: number): [number[], number] => {
  const out: number[] = [];
  while (out.length < n) {
    const run = v.getUint8(at++);
    const count = (run & 0x3f) + 1;
    const size = (run & 0xc0) === 0xc0 ? 4 : run & 0x80 ? 0 : run & 0x40 ? 2 : 1;
    for (let k = 0; k < count && out.length < n; k++) {
      out.push(size === 4 ? v.getInt32(at) : size === 2 ? v.getInt16(at) : size === 1 ? v.getInt8(at) : 0);
      at += size;
    }
  }
  return [out, at];
};

/** The untouched points of one contour moved with the touched ones around them, on each axis apart: between two
 * touched points by where the point lies between them, beyond both by the nearer one's delta. */
const infer = (orig: Point[], d: number[][], touched: boolean[], first: number, last: number) => {
  const idx: number[] = [];
  for (let i = first; i <= last; i++) if (touched[i]) idx.push(i);
  if (!idx.length || idx.length === last - first + 1) return;
  for (let k = 0; k < idx.length; k++) {
    const a = idx[k], b = idx[(k + 1) % idx.length];
    for (let i = a + 1; ; i++) {
      if (i > last) i = first;
      if (i === b) break;
      for (const ax of ['x', 'y'] as const) {
        const j = ax === 'x' ? 0 : 1;
        const pa = orig[a][ax], pb = orig[b][ax], c = orig[i][ax];
        const da = d[a][j], db = d[b][j];
        const [lo, hi, dlo, dhi] = pa <= pb ? [pa, pb, da, db] : [pb, pa, db, da];
        d[i][j] = lo === hi ? (da === db ? da : 0) : c <= lo ? dlo : c >= hi ? dhi : dlo + ((c - lo) / (hi - lo)) * (dhi - dlo);
      }
    }
  }
};

/** The outline of TrueType points as path commands at `size` per em, y down, origin at (x0, y0), as opentype.js draws
 * a glyph: an off-curve point between two off-curve points implies the on-curve point midway. */
const commandsOf = (pts: Point[], x0: number, y0: number, scale: number): Cmd[] => {
  const out: Cmd[] = [];
  const X = (x: number) => x0 + x * scale, Y = (y: number) => y0 - y * scale;
  const mid = (a: Point, b: Point) => ({x: (a.x + b.x) / 2, y: (a.y + b.y) / 2});
  let contour: Point[] = [];
  for (const p of pts) {
    contour.push(p);
    if (!p.lastPointOfContour) continue;
    const c = contour;
    contour = [];
    const lastPt = c[c.length - 1], firstPt = c[0];
    const start = lastPt.onCurve ? lastPt : firstPt.onCurve ? firstPt : mid(lastPt, firstPt);
    out.push({type: 'M', x: X(start.x), y: Y(start.y)});
    for (let i = 0; i < c.length; i++) {
      const cur = c[i], next = c[(i + 1) % c.length];
      if (cur.onCurve) out.push({type: 'L', x: X(cur.x), y: Y(cur.y)});
      else {
        const to = next.onCurve ? next : mid(cur, next);
        out.push({type: 'Q', x1: X(cur.x), y1: Y(cur.y), x: X(to.x), y: Y(to.y)});
      }
    }
    out.push({type: 'Z'});
  }
  return out;
};

/** The file's variations: its axes, their `avar` maps, and each glyph's regions with their deltas. */
const variationsOf = (buf: ArrayBuffer, base: Base) => {
  const axes = base.tables.fvar?.axes ?? [];
  const v = new DataView(buf);
  const t = tablesOf(v);
  if (!axes.length || t.gvar === undefined) return null;
  const g = t.gvar;
  const axisCount = v.getUint16(g + 4);
  const sharedCount = v.getUint16(g + 6);
  const sharedAt = g + v.getUint32(g + 8);
  const glyphCount = v.getUint16(g + 12);
  const long = v.getUint16(g + 14) & 1;
  const dataAt = g + v.getUint32(g + 16);
  const tuple = (at: number) => Array.from({length: axisCount}, (_, i) => f2dot14(v, at + 2 * i));
  const shared = Array.from({length: sharedCount}, (_, k) => tuple(sharedAt + 2 * axisCount * k));
  const offsetOf = (i: number) => (long ? v.getUint32(g + 20 + 4 * i) : 2 * v.getUint16(g + 20 + 2 * i));
  return {
    axes,
    maps: avarOf(v, t.avar, axes.length),
    /** The deltas of glyph `gid` at normalized `coords` for its `n` points (phantom points included), the untouched
     * points of each contour inferred when `contours` names the contours' last points. */
    deltas: (gid: number, n: number, coords: number[], orig: Point[] | null, contours: number[] | null) => {
      const d = Array.from({length: n}, () => [0, 0]);
      if (gid >= glyphCount) return d;
      const at = dataAt + offsetOf(gid);
      if (offsetOf(gid + 1) === offsetOf(gid)) return d;
      const head = v.getUint16(at);
      let p = at + v.getUint16(at + 2);
      let sharedPoints: number[] | null = null;
      if (head & 0x8000) [sharedPoints, p] = pointsAt(v, p);
      let h = at + 4;
      for (let k = 0; k < (head & 0x0fff); k++) {
        const size = v.getUint16(h), index = v.getUint16(h + 2);
        h += 4;
        let peak: number[];
        if (index & 0x8000) {
          peak = tuple(h);
          h += 2 * axisCount;
        } else peak = shared[index & 0x0fff];
        let start: number[] | undefined, end: number[] | undefined;
        if (index & 0x4000) {
          start = tuple(h);
          end = tuple(h + 2 * axisCount);
          h += 4 * axisCount;
        }
        const s = scalarOf(coords, peak, start, end);
        const next = p + size;
        if (s !== 0) {
          let q = p, pts = sharedPoints;
          if (index & 0x2000) [pts, q] = pointsAt(v, q);
          const count = pts ? pts.length : n;
          const [dx, q2] = deltasAt(v, q, count);
          const [dy] = deltasAt(v, q2, count);
          if (!pts || !orig || !contours) {
            for (let i = 0; i < count; i++) {
              const at2 = pts ? pts[i] : i;
              if (at2 < n) { d[at2][0] += s * dx[i]; d[at2][1] += s * dy[i]; }
            }
          } else {
            const own = Array.from({length: n}, () => [0, 0]);
            const touched = new Array<boolean>(n).fill(false);
            pts.forEach((at2, i) => {
              if (at2 < n) { own[at2] = [dx[i], dy[i]]; touched[at2] = true; }
            });
            let first = 0;
            for (const last of contours) {
              infer(orig, own, touched, first, last);
              first = last + 1;
            }
            for (let i = 0; i < n; i++) { d[i][0] += s * own[i][0]; d[i][1] += s * own[i][1]; }
          }
        }
        p = next;
      }
      return d;
    },
  };
};

/** The glyph of `base` at index `gid`, parsed: its points, or its components for a composite. */
const parsed = (base: Base, gid: number) => {
  const glyph = (base as any).glyphs.get(gid);
  glyph.getPath(0, 0, 1);
  return glyph as {index: number; advanceWidth: number; points?: Point[]; isComposite?: boolean; components?: Component[]; endPointIndices?: number[]};
};

/**
 * `base` at the instance `coords` names: a font whose glyphs are outlined and advanced at that instance and whose
 * `file` is `key`. Kerning is the file's default instance's.
 */
export const instanceOf = <F extends Base>(base: F, buf: ArrayBuffer, coords: Coords, key: string): F & {file: string} => {
  const vars = variationsOf(buf, base);
  const norm = vars ? vars.axes.map((a, i) => normalize(coords[a.tag] ?? a.defaultValue, a, vars.maps[i])) : [];
  if (!vars || norm.every((c) => c === 0)) return Object.assign(Object.create(base), {file: key});
  const memo = new Map<number, {points: Point[]; advance: number; shift: number}>();
  // the points of glyph gid at the instance, components placed, its advance, and its phantom origin's move
  const pointsOf = (gid: number): {points: Point[]; advance: number; shift: number} => {
    if (memo.has(gid)) return memo.get(gid)!;
    const glyph = parsed(base, gid);
    let points: Point[] = [];
    let d: number[][];
    if (glyph.isComposite && glyph.components) {
      const cs = glyph.components;
      d = vars.deltas(gid, cs.length + 4, norm, null, null);
      cs.forEach((c, k) => {
        const own = pointsOf(c.glyphIndex).points;
        const place = (q: Point, dx: number, dy: number): Point => ({
          x: c.xScale * q.x + c.scale01 * q.y + dx, y: c.scale10 * q.x + c.yScale * q.y + dy, onCurve: q.onCurve, lastPointOfContour: q.lastPointOfContour,
        });
        let dx = c.dx + d[k][0], dy = c.dy + d[k][1];
        if (c.matchedPoints && points[c.matchedPoints[0]] && own[c.matchedPoints[1]]) {
          const a = points[c.matchedPoints[0]], b = place(own[c.matchedPoints[1]], 0, 0);
          dx = a.x - b.x;
          dy = a.y - b.y;
        }
        points = points.concat(own.map((q) => place(q, dx, dy)));
      });
    } else {
      const orig = glyph.points ?? [];
      d = vars.deltas(gid, orig.length + 4, norm, orig, glyph.endPointIndices ?? null);
      points = orig.map((q, i) => ({...q, x: q.x + d[i][0], y: q.y + d[i][1]}));
    }
    const n = d.length - 4;
    const out = {points, advance: glyph.advanceWidth + d[n + 1][0] - d[n][0], shift: d[n][0]};
    memo.set(gid, out);
    return out;
  };
  const glyphs = new Map<number, any>();
  const vary = (g: any) => {
    if (!g) return g;
    if (!glyphs.has(g.index)) {
      const at = pointsOf(g.index);
      const pts = at.shift ? at.points.map((q) => ({...q, x: q.x - at.shift})) : at.points;
      glyphs.set(g.index, Object.assign(Object.create(g), {
        advanceWidth: at.advance,
        getPath: (x = 0, y = 0, size = 72) => ({commands: commandsOf(pts, x, y, size / base.unitsPerEm)}),
      }));
    }
    return glyphs.get(g.index);
  };
  return Object.assign(Object.create(base), {
    file: key,
    charToGlyph: (c: string) => vary(base.charToGlyph(c)),
    stringToGlyphs: (s: string) => base.stringToGlyphs(s).map(vary),
  });
};
