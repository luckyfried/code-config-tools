import React from 'react';
import {faceStyle, useMotion, useSys} from './system';
import type {RoutePoint} from './types';

type Box = {x: number; y: number; w: number; h: number};
type XY = [number, number];

/**
 * The trip's points projected into a box: equirectangular, longitude scaled by the cosine of the mean latitude,
 * fitted with padding and centered. A single point (or points a few meters apart) gets a small span around it.
 */
export const project = (pts: RoutePoint[], box: Box, pad = 0.14): XY[] => {
  if (!pts.length) return [];
  const lat0 = pts.reduce((a, p) => a + p.lat, 0) / pts.length;
  const kx = Math.cos((lat0 * Math.PI) / 180);
  const xs = pts.map((p) => p.lon * kx);
  const ys = pts.map((p) => -p.lat);
  const minx = Math.min(...xs), maxx = Math.max(...xs), miny = Math.min(...ys), maxy = Math.max(...ys);
  const sx = Math.max(maxx - minx, 0.02), sy = Math.max(maxy - miny, 0.02);
  const iw = box.w * (1 - 2 * pad), ih = box.h * (1 - 2 * pad);
  const k = Math.min(iw / sx, ih / sy);
  const cx = (minx + maxx) / 2, cy = (miny + maxy) / 2;
  return xs.map((x, i) => [box.x + box.w / 2 + (x - cx) * k, box.y + box.h / 2 + (ys[i] - cy) * k]);
};

/** The route as a sampled path: each leg a gentle arc, the samples and their running length. */
const samplePath = (xy: XY[]) => {
  const pts: XY[] = xy.length ? [xy[0]] : [];
  const at: number[] = [0];
  const legEnd: number[] = [0];
  for (let i = 1; i < xy.length; i++) {
    const [ax, ay] = xy[i - 1];
    const [bx, by] = xy[i];
    const dx = bx - ax, dy = by - ay;
    const len = Math.hypot(dx, dy);
    const bend = (i % 2 ? 1 : -1) * 0.18 * len;
    const mx = (ax + bx) / 2 - (dy / Math.max(1, len)) * bend;
    const my = (ay + by) / 2 + (dx / Math.max(1, len)) * bend;
    for (let k = 1; k <= 24; k++) {
      const t = k / 24;
      const x = (1 - t) * (1 - t) * ax + 2 * (1 - t) * t * mx + t * t * bx;
      const y = (1 - t) * (1 - t) * ay + 2 * (1 - t) * t * my + t * t * by;
      const [px, py] = pts[pts.length - 1];
      at.push(at[at.length - 1] + Math.hypot(x - px, y - py));
      pts.push([x, y]);
    }
    legEnd.push(at[at.length - 1]);
  }
  return {pts, at, legEnd, total: at[at.length - 1] ?? 0};
};

const pointAt = (s: ReturnType<typeof samplePath>, L: number): XY => {
  if (!s.pts.length) return [0, 0];
  for (let i = 1; i < s.pts.length; i++) {
    if (s.at[i] >= L) {
      const t = (L - s.at[i - 1]) / Math.max(1e-6, s.at[i] - s.at[i - 1]);
      return [s.pts[i - 1][0] + (s.pts[i][0] - s.pts[i - 1][0]) * t, s.pts[i - 1][1] + (s.pts[i][1] - s.pts[i - 1][1]) * t];
    }
  }
  return s.pts[s.pts.length - 1];
};

/**
 * Their route drawn in their palette from their own coordinates: a faint graticule, the whole route as a ghost,
 * the part traveled so far drawn solid (from point upto[0] to point upto[1] across progress 0..1), a dot at each
 * place reached with its name, and a bright head where the line is drawing. No map tiles: nothing is fetched.
 */
type Spot = {x: number; y: number; anchor: 'start' | 'middle' | 'end'};

/**
 * Where each place's name sits: beside its first dot, on the first side (right, left, above, below) whose box
 * touches no name already placed and no other dot, so two places a few kilometers apart never print over each other.
 */
const placeLabels = (points: RoutePoint[], xy: XY[], box: Box, size: number, stroke: number): (Spot | null)[] => {
  const taken: [number, number, number, number][] = [];
  const named = new Set<string>();
  const gap = stroke * 2.6;
  const hits = (r: [number, number, number, number], self: number) =>
    taken.some((t) => r[0] < t[2] && r[2] > t[0] && r[1] < t[3] && r[3] > t[1]) ||
    xy.some((q, j) => j !== self && (points[j].place ?? '') !== (points[self].place ?? '') &&
      q[0] > r[0] - stroke && q[0] < r[2] + stroke && q[1] > r[1] - stroke && q[1] < r[3] + stroke);
  return xy.map((p, i) => {
    const place = points[i].place ?? '';
    if (!place || named.has(place)) return null;
    named.add(place);
    const w = place.length * size * 0.62;
    const h = size * 1.1;
    const right = p[0] < box.x + box.w * 0.62;
    const sides: [Spot, [number, number, number, number]][] = [
      [{x: p[0] + gap, y: p[1] + size * 0.36, anchor: 'start'}, [p[0] + gap, p[1] - h / 2, p[0] + gap + w, p[1] + h / 2]],
      [{x: p[0] - gap, y: p[1] + size * 0.36, anchor: 'end'}, [p[0] - gap - w, p[1] - h / 2, p[0] - gap, p[1] + h / 2]],
      [{x: p[0], y: p[1] - gap, anchor: 'middle'}, [p[0] - w / 2, p[1] - gap - h, p[0] + w / 2, p[1] - gap]],
      [{x: p[0], y: p[1] + gap + size * 0.8, anchor: 'middle'}, [p[0] - w / 2, p[1] + gap, p[0] + w / 2, p[1] + gap + h]],
    ];
    if (!right) sides.unshift(sides.splice(1, 1)[0]);
    const pick = sides.find(([, r]) => !hits(r, i)) ?? sides[0];
    taken.push(pick[1]);
    return pick[0];
  });
};

export const RouteMap: React.FC<{
  points: RoutePoint[];
  upto?: [number, number];
  progress: number;
  box: Box;
  width: number;
  height: number;
  stroke?: number;
  labels?: boolean;
  labelSize?: number;
  color?: string;
  ink?: string;
  pad?: number;
}> = ({points, upto, progress, box, width, height, stroke = 8, labels = true, labelSize, color, ink, pad}) => {
  const {system} = useSys();
  const {pop} = useMotion();
  const xy = project(points, box, pad);
  const s = samplePath(xy);
  const [a, b] = upto ?? [0, Math.max(0, points.length - 1)];
  const from = s.legEnd[Math.min(a, s.legEnd.length - 1)] ?? 0;
  const to = s.legEnd[Math.min(b, s.legEnd.length - 1)] ?? 0;
  const L = from + (to - from) * Math.max(0, Math.min(1, progress));
  const d = s.pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
  const head = pointAt(s, L);
  const c = color ?? system.colors.accent;
  const k = ink ?? system.colors.ink;
  const size = labelSize ?? system.scale.label;
  const step = Math.max(box.w, box.h) / 6;
  const grid: React.ReactNode[] = [];
  for (let x = box.x; x <= box.x + box.w + 1; x += step) grid.push(<line key={`gx${x}`} x1={x} y1={box.y} x2={x} y2={box.y + box.h} />);
  for (let y = box.y; y <= box.y + box.h + 1; y += step) grid.push(<line key={`gy${y}`} x1={box.x} y1={y} x2={box.x + box.w} y2={y} />);
  const spots = placeLabels(points, xy, box, size, stroke);
  const marks = xy.map((p, i) => {
    const reached = s.legEnd[i] <= L + 0.5;
    const place = points[i].place ?? '';
    const spot = spots[i];
    const q = reached ? pop(0) : 0;
    return (
      <g key={i} opacity={reached ? 1 : 0.35}>
        <circle cx={p[0]} cy={p[1]} r={stroke * (reached ? 1.25 : 0.8)} fill={reached ? c : 'none'} stroke={c} strokeWidth={stroke * 0.35} />
        {labels && spot ? (
          <text x={spot.x} y={spot.y} textAnchor={spot.anchor}
            style={{...faceStyle(system.text), fontSize: size, fill: k, opacity: reached ? 0.5 + 0.5 * q : 0.45, textTransform: 'lowercase'}}>
            {place}
          </text>
        ) : null}
      </g>
    );
  });
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
      <g stroke={k} strokeOpacity={0.09} strokeWidth={1.5}>{grid}</g>
      {xy.length > 1 ? (
        <>
          <path d={d} fill="none" stroke={k} strokeOpacity={0.22} strokeWidth={stroke * 0.4} strokeDasharray={`${stroke * 0.9} ${stroke * 1.6}`} strokeLinecap="round" />
          <path d={d} fill="none" stroke={c} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
            strokeDasharray={`${L.toFixed(1)} ${(s.total + 10).toFixed(1)}`} />
        </>
      ) : null}
      {marks}
      {xy.length ? <circle cx={head[0]} cy={head[1]} r={stroke * 1.9} fill={k} stroke={c} strokeWidth={stroke * 0.6} /> : null}
    </svg>
  );
};
