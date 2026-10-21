import React, {useEffect, useRef} from 'react';
import {Img} from 'remotion';
import {RETRIES} from './layer';
import {axesOf, hash, src, useColor, useMotion, useSafe, useSys} from './system';
import type {Face} from './types';

/**
 * A photograph's place in a box. `aspect` is the source's height over its width; `crop` is [x, y, w]: the source's
 * left and top edges of what the box shows, and the share of the source's width it shows, all in fractions of the
 * source (absent: the cover crop, centred). `at(u, v)` maps a point of the source, in fractions, to box pixels, so
 * anything drawn there stays on that point of the picture whatever the crop.
 */
export const fitPhoto = (aspect: number, bw: number, bh: number, crop?: [number, number, number]) => {
  let imgW: number;
  let cx: number;
  let cy: number;
  if (crop) {
    imgW = bw / crop[2];
    cx = crop[0];
    cy = crop[1];
  } else {
    imgW = Math.max(bw, bh / aspect);
    cx = (1 - bw / imgW) / 2;
    cy = (1 - bh / (imgW * aspect)) / 2;
  }
  const imgH = imgW * aspect;
  return {imgW, imgH, left: -cx * imgW, top: -cy * imgH, at: (u: number, v: number): [number, number] => [(u - cx) * imgW, (v - cy) * imgH]};
};

/** The photograph laid into its box by `fitPhoto`, never moving inside it: whatever is drawn on it stays registered. */
export const PhotoIn: React.FC<{file: string; aspect: number; w: number; h: number; crop?: [number, number, number]; filter?: string}> = ({
  file,
  aspect,
  w,
  h,
  crop,
  filter,
}) => {
  const f = fitPhoto(aspect, w, h, crop);
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden'}}>
      <Img src={src(file)} maxRetries={RETRIES}
        style={{position: 'absolute', left: f.left, top: f.top, width: f.imgW, height: f.imgH, maxWidth: 'none', display: 'block', filter}} />
    </div>
  );
};

type Pt = [number, number];

/** A smooth path through the points (Catmull-Rom as cubic Béziers). */
const smooth = (p: Pt[]) => {
  if (p.length < 3) return p.map((q, i) => `${i ? 'L' : 'M'}${q[0].toFixed(1)},${q[1].toFixed(1)}`).join(' ');
  let d = `M${p[0][0].toFixed(1)},${p[0][1].toFixed(1)}`;
  for (let i = 0; i < p.length - 1; i++) {
    const a = p[Math.max(0, i - 1)];
    const b = p[i];
    const c = p[i + 1];
    const e = p[Math.min(p.length - 1, i + 2)];
    const c1 = [b[0] + (c[0] - a[0]) / 6, b[1] + (c[1] - a[1]) / 6];
    const c2 = [c[0] - (e[0] - b[0]) / 6, c[1] - (e[1] - b[1]) / 6];
    d += ` C${c1[0].toFixed(1)},${c1[1].toFixed(1)} ${c2[0].toFixed(1)},${c2[1].toFixed(1)} ${c[0].toFixed(1)},${c[1].toFixed(1)}`;
  }
  return d;
};

/** A hand-drawn loop: a little more than one turn of a wobbling ellipse, its ends overshooting each other. */
const loopPath = (c: Pt, rx: number, ry: number, seed: number) => {
  const pts: Pt[] = [];
  const a0 = -Math.PI * (0.6 + seed * 0.3);
  const turn = Math.PI * 2 * 1.13;
  const n = 48;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const a = a0 + turn * t;
    const wob = 1 + 0.035 * Math.sin(a * 3 + seed * 9) + 0.06 * (t - 0.5);
    pts.push([c[0] + Math.cos(a) * rx * wob, c[1] + Math.sin(a) * ry * wob]);
  }
  return smooth(pts);
};

export type Mark = {
  kind: 'route' | 'loop' | 'brackets' | 'cross' | 'horizon' | 'text';
  /** musical beat after the layer's entrance where the mark starts drawing */
  at?: number;
  color?: string;
  width?: number;
  [k: string]: any;
};

const draw = (p: number): React.SVGProps<SVGPathElement> => ({pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - p});

/**
 * Marks drawn on a photograph in its own coordinates (fractions of the source; points outside 0 to 1 leave the
 * picture and carry on over the frame).
 * route    a line through `points`, drawn on, with a dark casing and a roundel at each of `stops` (`hollow`: a ring
 *          that leaves what it marks visible)
 * loop     a grease-pencil loop around `c` with radii `r` [rx, ry] in fractions of the source's width
 * brackets crop corners at `rect` [u0, v0, u1, v1]
 * cross    a grease-pencil cross over `rect`
 * horizon  a hairline at the source's height `v`, from `from` to `to` in fractions of the frame's width
 * text     words at `pos` in the tone's display or text face, `size` px, `anchor` start, middle or end, `lines` stacked;
 *          `plate` sets them on a block of that palette color, padded by `pad` of their width each side; `move` rise
 *          lifts them into place through a slot at their own line, `move` wipe uncovers them from the anchor side,
 *          both over `beats` (0.5); without a move they fade in
 * Text that leaves the format's safe area, measured after its rotation, is reported as SAFE_BREACH.
 */
export const Marks: React.FC<{marks: Mark[]; aspect: number; w: number; h: number; crop?: [number, number, number]; start: number; id: string; origin: Pt}> = ({
  marks,
  aspect,
  w,
  h,
  crop,
  start,
  id,
  origin,
}) => {
  const m = useMotion();
  const {system, beat, format} = useSys();
  const color = useColor();
  const safe = useSafe();
  const W0 = safe.W;
  const f = fitPhoto(aspect, w, h, crop);
  const ref = useRef<SVGSVGElement>(null);
  const progress = (k: Mark, beats = 1) => m.tween(0, 1, start + m.at(k.at ?? 0), Math.max(1, Math.round(m.pulse * beats)), 'move');
  useEffect(() => {
    const el = ref.current;
    if (!el || m.frame < start + m.pulse * 2) return;
    el.querySelectorAll<SVGTextElement>('text[data-name]').forEach((t) => {
      const b = t.getBBox();
      const a = (Number(t.dataset.rotate ?? 0) * Math.PI) / 180;
      const px = Number(t.getAttribute('x'));
      const py = Number(t.getAttribute('y'));
      const corners = [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]].map(([cx, cy]) => [
        px + (cx - px) * Math.cos(a) - (cy - py) * Math.sin(a),
        py + (cx - px) * Math.sin(a) + (cy - py) * Math.cos(a),
      ]);
      const x0 = origin[0] + Math.min(...corners.map((c) => c[0]));
      const y0 = origin[1] + Math.min(...corners.map((c) => c[1]));
      const x1 = origin[0] + Math.max(...corners.map((c) => c[0]));
      const y1 = origin[1] + Math.max(...corners.map((c) => c[1]));
      const out = x0 < safe.left - 1 || y0 < safe.top - 1 || x1 > safe.W - safe.right + 1 || y1 > safe.H - safe.bottom + 1;
      if (out) console.log(`SAFE_BREACH ${JSON.stringify({format, beat: beat?.id, box: t.dataset.name, frame: m.frame, box_px: [x0, y0, x1 - x0, y1 - y0].map(Math.round)})}`);
    });
  });
  const rough = `rough-${id}`;
  const face = (k: Mark): Face => (k.face === 'text' ? system.text : system.display);
  return (
    <svg ref={ref} width={w} height={h} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
      <defs>
        <filter id={rough} x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={Math.round(hash(id) * 100)} result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="5" />
        </filter>
      </defs>
      {marks.map((k, i) => {
        const c = color(k.color, 'accent');
        if (k.kind === 'route') {
          const pts = (k.points as Pt[]).map(([u, v]) => f.at(u, v));
          const d = smooth(pts);
          const p = progress(k, k.beats ?? 2);
          const wd = k.width ?? 14;
          return (
            <g key={i}>
              <path d={d} fill="none" stroke="#000" strokeOpacity={0.28} strokeWidth={wd + 10} strokeLinecap="round" strokeLinejoin="round" {...draw(p)} />
              <path d={d} fill="none" stroke={c} strokeWidth={wd} strokeLinecap="round" strokeLinejoin="round" {...draw(p)} />
              {(k.stops ?? []).map((s: {at: Pt; r?: number; t?: number; hollow?: boolean}, j: number) => {
                const [x, y] = f.at(s.at[0], s.at[1]);
                const on = m.hit(start + m.at(k.at ?? 0) + Math.round(m.pulse * (k.beats ?? 2) * (s.t ?? 1)));
                if (on <= 0) return null;
                const r = (s.r ?? wd * 1.7) * Math.min(1.2, on);
                return (
                  <g key={j}>
                    <circle cx={x} cy={y} r={r + wd * 0.35} fill={s.hollow ? 'none' : '#000'} stroke={s.hollow ? '#000' : 'none'}
                      strokeOpacity={0.28} strokeWidth={wd * 1.3} fillOpacity={0.25} />
                    <circle cx={x} cy={y} r={r} fill={s.hollow ? 'none' : system.colors.bg} stroke={c} strokeWidth={wd * 0.62} />
                  </g>
                );
              })}
            </g>
          );
        }
        if (k.kind === 'loop') {
          const [x, y] = f.at(k.c[0], k.c[1]);
          const rx = k.r[0] * f.imgW;
          const ry = k.r[1] * f.imgW;
          const p = progress(k, k.beats ?? 0.75);
          const seed = hash(`${id}-${i}`);
          return (
            <g key={i} filter={`url(#${rough})`} opacity={0.94}>
              <path d={loopPath([x, y], rx, ry, seed)} fill="none" stroke={c} strokeWidth={k.width ?? 9} strokeLinecap="round" {...draw(p)} />
              <path d={loopPath([x + 2, y - 1], rx * 0.985, ry * 1.01, seed)} fill="none" stroke={c} strokeOpacity={0.5} strokeWidth={(k.width ?? 9) * 0.45}
                strokeLinecap="round" {...draw(p)} />
            </g>
          );
        }
        if (k.kind === 'brackets' || k.kind === 'cross') {
          const [x0, y0] = f.at(k.rect[0], k.rect[1]);
          const [x1, y1] = f.at(k.rect[2], k.rect[3]);
          const p = progress(k, k.beats ?? 0.75);
          const wd = k.width ?? 8;
          if (k.kind === 'cross') {
            return (
              <g key={i} filter={`url(#${rough})`} opacity={0.92} stroke={c} strokeWidth={wd} strokeLinecap="round" fill="none">
                <path d={`M${x0},${y0} L${x1},${y1}`} {...draw(Math.min(1, p * 2))} />
                <path d={`M${x1},${y0} L${x0},${y1}`} {...draw(Math.max(0, p * 2 - 1))} />
              </g>
            );
          }
          const l = (k.len ?? 0.22) * Math.min(x1 - x0, y1 - y0);
          const corners = [
            `M${x0},${y0 + l} L${x0},${y0} L${x0 + l},${y0}`,
            `M${x1 - l},${y0} L${x1},${y0} L${x1},${y0 + l}`,
            `M${x1},${y1 - l} L${x1},${y1} L${x1 - l},${y1}`,
            `M${x0 + l},${y1} L${x0},${y1} L${x0},${y1 - l}`,
          ];
          return (
            <g key={i} filter={`url(#${rough})`} opacity={0.94} stroke={c} strokeWidth={wd} strokeLinecap="round" strokeLinejoin="round" fill="none">
              {corners.map((d, j) => <path key={j} d={d} {...draw(Math.max(0, Math.min(1, p * 4 - j)))} />)}
            </g>
          );
        }
        if (k.kind === 'horizon') {
          const y = f.at(0, k.v)[1];
          const xa = (k.from ?? 0) * safe.W - origin[0];
          const xb = (k.to ?? 1) * safe.W - origin[0];
          const p = progress(k, k.beats ?? 2);
          return <path key={i} d={`M${xa},${y} L${xb},${y}`} stroke={c} strokeWidth={k.width ?? 2} strokeOpacity={k.opacity ?? 0.9} {...draw(p)} />;
        }
        if (k.kind === 'text') {
          const [x, y] = f.at(k.pos[0], k.pos[1]);
          const fc = face(k);
          const size: number = k.size ?? system.scale.h2;
          const lines: string[] = k.lines ?? [String(k.text ?? '')];
          const lh = size * (k.leading ?? fc.lineHeight);
          const move: string | undefined = k.move;
          const p = progress(k, move ? (k.beats ?? 0.5) : 0.75);
          const plate = k.plate ? `plate-${id}-${i}` : undefined;
          const padX = (k.pad ?? 0.07);
          const anchor: 'start' | 'middle' | 'end' = k.anchor ?? 'start';
          const top = y - size * 1.1;
          const bot = y + size * 0.42 + lh * (lines.length - 1);
          const reach = size * (0.64 * Math.max(...lines.map((ln) => ln.length)) * (1 + 2 * padX) + 0.6);
          const wiped = reach * p;
          const clipX = anchor === 'end' ? x + size * 0.3 - wiped : anchor === 'middle' ? x - wiped / 2 : x - size * 0.3;
          const clip = move === 'rise' ? {x: x - 4 * w, y: top, width: 8 * w + 4 * W0, height: bot - top}
            : move === 'wipe' ? {x: clipX, y: top - size * 0.2, width: wiped, height: bot - top + size * 0.4} : undefined;
          const clipId = clip ? `clip-${id}-${i}` : undefined;
          const shown = move ? 1 : p;
          return (
            <g key={i} transform={k.rotate ? `rotate(${k.rotate} ${x} ${y})` : undefined}>
            {clip ? <clipPath id={clipId}><rect {...clip} /></clipPath> : null}
            <g clipPath={clipId ? `url(#${clipId})` : undefined}>
            <g transform={move === 'rise' ? `translate(0 ${((1 - p) * (bot - top)).toFixed(1)})` : undefined}>
            <g filter={plate ? `url(#${plate})` : undefined} opacity={plate ? shown : 1}>
            {plate ? (
              <filter id={plate} x={-padX} y={-0.06} width={1 + 2 * padX} height={1.12}>
                <feFlood floodColor={color(k.plate, 'bg')} result="plate" />
                <feMerge><feMergeNode in="plate" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            ) : null}
            <text data-name={k.name ?? `text-${i}`} data-rotate={k.rotate ?? 0} x={x} y={y} textAnchor={anchor}
              style={{fontFamily: `'${fc.family}'`, fontWeight: k.weight ?? fc.weight, fontSize: size, letterSpacing: `${k.tracking ?? fc.tracking}em`,
                fontVariationSettings: k.axes ? Object.entries(k.axes as Record<string, number>).map(([a, v]) => `'${a}' ${v}`).join(', ') : axesOf(fc),
                fontFeatureSettings: '"kern" 1, "liga" 1, "tnum" 1', textTransform: k.case ?? (fc.case === 'none' ? undefined : fc.case)}}
              fill={c} fillOpacity={(k.opacity ?? 1) * (plate ? 1 : shown)}>
              {lines.map((ln, j) => <tspan key={j} x={x} dy={j ? lh : 0}>{ln}</tspan>)}
            </text>
            </g>
            </g>
            </g>
            </g>
          );
        }
        return null;
      })}
    </svg>
  );
};
