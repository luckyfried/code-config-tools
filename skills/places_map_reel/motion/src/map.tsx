import React, {useEffect, useState} from 'react';
import {continueRender, delayRender, staticFile} from 'remotion';
import {faceStyle, useSys} from './system';
import type {Cam, MapPin} from './types';

type Land = {paths: string[]};
let cache: Land | null = null;
let pending: Promise<Land> | null = null;

/** The land shapes (Natural Earth, public domain) the kit ships, in world units; loaded once per render. */
export const useLand = (file: string): Land | null => {
  const [land, setLand] = useState<Land | null>(cache);
  const [handle] = useState(() => (cache ? null : delayRender(`land ${file}`)));
  useEffect(() => {
    if (cache) {
      if (handle !== null) continueRender(handle);
      return;
    }
    pending = pending ?? fetch(staticFile(file)).then((r) => r.json());
    pending
      .then((d) => {
        cache = d;
        setLand(d);
        if (handle !== null) continueRender(handle);
      })
      .catch((e) => {
        console.log(`MAP_ERROR ${String(e)}`);
        setLand({paths: []});
        if (handle !== null) continueRender(handle);
      });
  }, []);
  return land;
};

export type View = {cam: Cam; w: number; h: number};

/** World units (web mercator, 0 to 1000 across the world) to pixels in a view. */
export const project = (v: View, x: number, y: number): [number, number] => {
  const k = v.w / v.cam[2];
  return [(x - v.cam[0]) * k + v.w / 2, (y - v.cam[1]) * k + v.h / 2];
};

/**
 * A camera move from a to b: the center glides, the span zooms on a log scale, and a long move pulls out
 * mid-way so the viewer keeps both ends in sight.
 */
export const lerpCam = (a: Cam, b: Cam, t: number): Cam => {
  const d = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const big = Math.max(a[2], b[2]);
  const bump = d > big * 0.6 ? Math.min(1.2, d / big - 0.6) * Math.sin(Math.PI * t) : 0;
  const span = Math.exp(Math.log(a[2]) + (Math.log(b[2]) - Math.log(a[2])) * t) * (1 + bump);
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, span];
};

const mercY = (lat: number) => (1 - Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360)) / Math.PI) / 2 * 1000;

/** The sea, a light graticule and the land, in pixel space for the view. Children draw on top in pixels. */
export const MapCanvas: React.FC<{
  view: View;
  sea: string;
  land: string;
  coast: string;
  graticule?: string;
  children?: React.ReactNode;
  style?: React.CSSProperties;
}> = ({view, sea, land, coast, graticule, children, style}) => {
  const {board} = useSys();
  const shapes = useLand(board.map.land);
  const k = view.w / view.cam[2];
  const x0 = view.cam[0] - view.w / 2 / k;
  const y0 = view.cam[1] - view.h / 2 / k;
  const degPx = (1000 / 360) * k;
  const step = degPx > 160 ? 2 : degPx > 50 ? 5 : degPx > 15 ? 10 : 30;
  const lines: React.ReactNode[] = [];
  if (graticule) {
    const lonA = Math.floor((x0 / 1000) * 360 - 180);
    const lonB = Math.ceil(((x0 + view.w / k) / 1000) * 360 - 180);
    for (let lon = Math.ceil(lonA / step) * step; lon <= lonB; lon += step) {
      const px = (((lon + 180) / 360) * 1000 - x0) * k;
      lines.push(<line key={`o${lon}`} x1={px} x2={px} y1={0} y2={view.h} stroke={graticule} strokeWidth={1} />);
    }
    for (let lat = -80; lat <= 80; lat += step) {
      const py = (mercY(lat) - y0) * k;
      if (py < -2 || py > view.h + 2) continue;
      lines.push(<line key={`a${lat}`} x1={0} x2={view.w} y1={py} y2={py} stroke={graticule} strokeWidth={1} />);
    }
  }
  return (
    <svg width={view.w} height={view.h} viewBox={`0 0 ${view.w} ${view.h}`} style={{position: 'absolute', left: 0, top: 0, overflow: 'hidden', ...style}}>
      <rect x={0} y={0} width={view.w} height={view.h} fill={sea} />
      {lines}
      <g transform={`translate(${-x0 * k} ${-y0 * k}) scale(${k})`}>
        {(shapes?.paths ?? []).map((d, i) => (
          <path key={i} d={d} fill={land} stroke={coast} strokeWidth={1.4 / k} strokeLinejoin="round" />
        ))}
      </g>
      {children}
    </svg>
  );
};

/** A leg drawn up to t (0 to 1) of its length, in pixels. */
export const legPath = (v: View, pts: [number, number][], t: number): string => {
  if (t <= 0 || pts.length < 2) return '';
  const n = pts.length - 1;
  const upto = Math.min(n, t * n);
  const whole = Math.floor(upto);
  const out: [number, number][] = [];
  for (let i = 0; i <= whole; i++) out.push(project(v, pts[i][0], pts[i][1]));
  if (whole < n) {
    const f = upto - whole;
    const a = pts[whole];
    const b = pts[whole + 1];
    out.push(project(v, a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f));
  }
  return 'M' + out.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join('L');
};

/** The head of a leg drawn up to t, in pixels. */
export const legHead = (v: View, pts: [number, number][], t: number): [number, number] => {
  const n = pts.length - 1;
  const upto = Math.max(0, Math.min(n, t * n));
  const i = Math.min(n - 1, Math.floor(upto));
  const f = upto - i;
  const a = pts[i];
  const b = pts[i + 1] ?? a;
  return project(v, a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f);
};

/** A place's name beside its pin, on the side storyboard.py chose so no two labels collide. */
export const PinLabel: React.FC<{
  pin: MapPin;
  at: [number, number];
  side: string;
  size: number;
  color: string;
  halo: string;
  opacity?: number;
}> = ({pin, at, side, size, color, halo, opacity = 1}) => {
  const {system} = useSys();
  const g = size * 0.5;
  const [x, y] = at;
  const pos = {
    right: {x: x + g, y, anchor: 'start', base: 'central'},
    left: {x: x - g, y, anchor: 'end', base: 'central'},
    above: {x, y: y - g, anchor: 'middle', base: 'alphabetic'},
    below: {x, y: y + g, anchor: 'middle', base: 'hanging'},
  }[side as 'right'] ?? {x: x + g, y, anchor: 'start', base: 'central'};
  const f = faceStyle(system.text);
  return (
    <text
      x={pos.x}
      y={pos.y}
      textAnchor={pos.anchor as any}
      dominantBaseline={pos.base as any}
      fontFamily={`'${system.text.family}'`}
      fontWeight={600}
      fontSize={size}
      letterSpacing={f.letterSpacing as string}
      fill={color}
      stroke={halo}
      strokeWidth={size * 0.22}
      strokeLinejoin="round"
      paintOrder="stroke"
      opacity={opacity}
    >
      {pin.name}
    </text>
  );
};
