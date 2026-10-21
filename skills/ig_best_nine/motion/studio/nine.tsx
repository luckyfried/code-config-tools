import React, {useEffect, useRef, useState} from 'react';
import {continueRender, delayRender, Easing, interpolate, useCurrentFrame} from 'remotion';
import {useLayer} from '../system/layer';
import {fitPhoto} from '../system/marks';
import {axesOf, src, tint, useColor, useMotion, useSafe, useSys} from '../system/system';
import type {Face, Layer} from '../system/types';

/**
 * The best nine's own layers: the objects that carry a person's nine posts. Every position is in px of the format's
 * frame, computed by the storyboard from the posts' likes, dates and ranks; every photograph is placed by its focus point
 * (`focus` [u, v] in fractions of the source) or by an explicit `crop` [x, y, w], so the subject decides the crop
 * whatever the box. Every word is drawn with a `data-name` and checked against the format's safe area.
 */

type P = {layer: Layer};
type Pt = [number, number];
type Box = [number, number, number, number];

/**
 * Text that leaves the format's safe area, measured from its box in the frame, is reported as SAFE_BREACH with the
 * frame of its beat it was seen in. While the camera moves between two framings nothing is reported: a move may pass
 * through a crop, and the framing it comes to rest in is checked. Text wholly
 * outside the frame is out of the shot, not out of the safe area, and is not reported; text the frame edge cuts is.
 */
const useSafeCheck = (ref: React.RefObject<SVGSVGElement | null>, settled: boolean) => {
  const {beat, format} = useSys();
  const safe = useSafe();
  const frame = useCurrentFrame();
  const {pulse} = useMotion();
  const move = (beat as {viewTo?: unknown; viewMove?: [number, number]} | undefined)?.viewTo ? (beat as {viewMove?: [number, number]}).viewMove ?? [0, 1] : null;
  const moving = move !== null && frame > move[0] * pulse && frame < (move[0] + move[1]) * pulse;
  useEffect(() => {
    const el = ref.current;
    if (!el || !settled || moving) return;
    el.querySelectorAll<SVGGraphicsElement>('[data-name]').forEach((t) => {
      const r = t.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;
      const host = (el.closest('[data-frame]') ?? el).getBoundingClientRect();
      const k = safe.W / Math.max(1, host.width);
      const [x0, y0, x1, y1] = [(r.left - host.left) * k, (r.top - host.top) * k, (r.right - host.left) * k, (r.bottom - host.top) * k];
      if (x1 <= 0 || y1 <= 0 || x0 >= safe.W || y0 >= safe.H) return;
      if (x0 < safe.left - 1 || y0 < safe.top - 1 || x1 > safe.W - safe.right + 1 || y1 > safe.H - safe.bottom + 1)
        console.log(`SAFE_BREACH ${JSON.stringify({format, beat: beat?.id, frame, box: t.dataset.name, box_px: [x0, y0, x1 - x0, y1 - y0].map(Math.round)})}`);
    });
  });
};

/** Holds the render until an SVG image has loaded, so no frame is captured with the photograph missing. */
const useImageGate = (file: string | undefined) => {
  const [handle] = useState(() => (file ? delayRender(`image ${file}`) : null));
  const done = useRef(false);
  const release = () => {
    if (handle !== null && !done.current) {
      done.current = true;
      continueRender(handle);
    }
  };
  return {onLoad: release, onError: () => (console.log(`IMAGE_ERROR ${file}`), release())};
};

/** The widest window of the source that fills a box of `bw` x `bh`, tightened by `zoom`, centred on `focus` and kept inside the source. */
export const cropAround = (aspect: number, focus: Pt, bw: number, bh: number, zoom = 1): [number, number, number] => {
  const r = bh / Math.max(1, bw);
  const w = Math.min(1, aspect / r) / Math.max(1, zoom);
  const h = (w * r) / aspect;
  const clamp = (v: number, hi: number) => Math.max(0, Math.min(hi, v));
  return [clamp(focus[0] - w / 2, 1 - w), clamp(focus[1] - h / 2, 1 - h), w];
};

type Photo = {file: string; aspect: number; focus?: Pt; crop?: [number, number, number]; zoom?: number};

/** A photograph laid into a px box by its crop, clipped to `clip` (an SVG clip id) or to the box itself. */
const SvgPhoto: React.FC<{photo: Photo; box: Box; clip?: string; filter?: string}> = ({photo, box, clip, filter}) => {
  const gate = useImageGate(photo.file);
  const [x, y, w, h] = box;
  const crop = photo.crop ?? cropAround(photo.aspect, photo.focus ?? [0.5, 0.5], w, h, photo.zoom);
  const f = fitPhoto(photo.aspect, w, h, crop);
  const id = `ph-${photo.file.replace(/\W/g, '')}-${Math.round(x)}-${Math.round(y)}-${Math.round(w)}`;
  return (
    <g>
      {clip ? null : (
        <defs>
          <clipPath id={id}><rect x={x} y={y} width={w} height={h} /></clipPath>
        </defs>
      )}
      <g clipPath={`url(#${clip ?? id})`}>
        <image href={src(photo.file)} x={x + f.left} y={y + f.top} width={f.imgW} height={f.imgH} preserveAspectRatio="none"
          onLoad={gate.onLoad} onError={gate.onError} style={{filter}} />
      </g>
    </g>
  );
};

/** One line of type: `face` display or text, `size` px, baseline at `y`, optional variable `axes`, `weight`, `tracking` (em), `italic`. */
type Line = {
  text: string;
  x: number;
  y: number;
  size: number;
  face?: 'display' | 'text';
  color?: string;
  anchor?: 'start' | 'middle' | 'end';
  weight?: number;
  axes?: Record<string, number>;
  tracking?: number;
  italic?: boolean;
  name?: string;
  /** degrees the line is turned, clockwise on screen, about `pivot` px (its own origin when absent) */
  rotate?: number;
  pivot?: Pt;
  /** a figure that counts from the first number to the second over the third's beats from the line's start, quick and then
   * settling, never past it */
  count?: [number, number, number];
  /** [x, y, size] the line moves and resizes from while it counts, standing the whole time instead of rising */
  was?: [number, number, number];
};

/** A count as drive sets it: thousands grouped by a narrow space. */
const figure = (n: number) => Math.round(n).toLocaleString('en-US').replace(/,/g, '\u202f');

const lineStyle = (f: Face, l: Line): React.CSSProperties => ({
  fontFamily: `'${f.family}'`,
  fontWeight: l.weight ?? f.weight,
  fontSize: l.size,
  fontStyle: l.italic ? 'italic' : undefined,
  letterSpacing: `${l.tracking ?? f.tracking}em`,
  fontVariationSettings: l.axes ? Object.entries(l.axes).map(([a, v]) => `'${a}' ${v}`).join(', ') : axesOf(f),
  fontFeatureSettings: '"kern" 1, "liga" 1, "tnum" 1, "lnum" 1',
});

const useFaces = () => {
  const {system} = useSys();
  return (k: Line['face']) => (k === 'display' ? system.display : system.text);
};

/** A line of type that rises through its own baseline by `p` (0 to 1), turned on its pivot when it has a `rotate`. */
const Rise: React.FC<{line: Line; p: number; id: string; fill: string}> = ({line, p, id, fill}) => {
  const faces = useFaces();
  const top = line.y - line.size * 1.05;
  const h = line.size * 1.4;
  const turn = line.rotate ? `rotate(${line.rotate} ${(line.pivot ?? [line.x, line.y]).join(' ')})` : undefined;
  return (
    <g transform={turn}>
      <defs>
        <clipPath id={id}><rect x={-2000} y={top} width={5000} height={h} /></clipPath>
      </defs>
      <g clipPath={`url(#${id})`}>
        <text x={line.x} y={line.y + (1 - p) * h} textAnchor={line.anchor ?? 'start'} fill={fill} style={lineStyle(faces(line.face), line)}
          data-name={line.name ?? line.text}>
          {line.text}
        </text>
      </g>
    </g>
  );
};

/**
 * Words: lines of type set where the composition puts them (`lines`, px baselines), each rising through its baseline
 * on the layer's stagger from `at`, `beats` long. A line with a `count` counts its figure up or down as it enters, and
 * one with a `was` comes from that place and size, so a figure can carry across a cut.
 */
export const Words: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {W, H} = useSafe();
  const ref = useRef<SVGSVGElement>(null);
  const lines: Line[] = layer.lines ?? [];
  const dur = Math.max(1, Math.round(L.pulse * (layer.beats ?? 0.75)));
  const step = Math.round(L.pulse * (layer.step ?? 0.25));
  useSafeCheck(ref, L.frame >= L.start + dur + step * lines.length);
  return (
    <svg ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible', opacity: 1 - L.leave()}}>
      {lines.map((ln, i) => {
        const t0 = L.start + i * step;
        const rise = L.tween(0, 1, t0, dur, 'enter');
        if (!ln.count) return <Rise key={i} line={ln} id={`w-${layer.id}-${i}`} fill={color(ln.color ?? 'ink')} p={rise} />;
        const [a, b, beats] = ln.count;
        const q = interpolate(L.frame, [t0, t0 + Math.max(1, Math.round(L.pulse * beats))], [0, 1], {easing: Easing.out(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        const mix = (u: number, v: number) => u + (v - u) * q;
        const w = ln.was;
        const at = w ? {x: mix(w[0], ln.x), y: mix(w[1], ln.y), size: mix(w[2], ln.size)} : {x: ln.x, y: ln.y, size: ln.size};
        const shown = {...ln, ...at, text: figure(mix(a, b)), pivot: ln.rotate !== undefined ? ([at.x, at.y] as Pt) : ln.pivot};
        return <Rise key={i} line={shown} id={`w-${layer.id}-${i}`} fill={color(ln.color ?? 'ink')} p={w ? 1 : rise} />;
      })}
    </svg>
  );
};

/* ---------------------------------------------------------------- drive: the cut */

/**
 * Cut: one straight edge across the frame, meeting its left and right sides at `line` [yl, yr] px, a flat field of the
 * `field` color above it and, under it, the post's photograph laid whole at `place` [x, y, w, h] px, so the line the
 * photograph carries lies on the edge. The edge pivots from `from` (the edge before it) over `beats` from `at`, the
 * photograph moving with it from `fromPlace` when the shot before showed the same photograph, and the photograph pushes
 * in by `push` across the beat about the middle of the edge, which keeps its line on the edge.
 */
export const Cut: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {W, H} = useSafe();
  const [yl, yr] = layer.line as Pt;
  const [fl, fr] = (layer.from as Pt | undefined) ?? [yl, yr];
  const p = L.tween(0, 1, L.start, Math.max(1, Math.round(L.pulse * (layer.beats ?? 0.5))), 'move');
  const a = fl + (yl - fl) * p;
  const b = fr + (yr - fr) * p;
  const cy = (yl + yr) / 2;
  const push = 1 + (layer.push ?? 0.04) * Math.min(1, L.local / Math.max(1, L.duration));
  const to = layer.place as Box;
  const from = (layer.fromPlace as Box | undefined) ?? to;
  const box = to.map((v, i) => from[i] + (v - from[i]) * p) as Box;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      {layer.photo ? (
        <g transform={`translate(${W / 2} ${cy}) scale(${push}) translate(${-W / 2} ${-cy})`}>
          <SvgPhoto photo={{...(layer.photo as Photo), crop: [0, 0, 1]}} box={box} />
        </g>
      ) : null}
      <polygon points={`0,0 ${W},0 ${W},${b} 0,${a}`} fill={color(layer.field ?? 'paper')} />
    </svg>
  );
};

/**
 * Slice: a photograph inside the four-sided piece `poly` of the frame (px corners: top left, top right, bottom right,
 * bottom left, its sides upright), laid whole in the px box `place`. It is uncovered from its top edge down over
 * `beats` from `at`, quick from the start so a row reads as soon as it begins.
 */
export const Slice: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {W, H} = useSafe();
  const p = Math.min(1, L.tween(0, 1, L.start, Math.max(1, Math.round(L.pulse * (layer.beats ?? 0.5))), 'enter'));
  if (p <= 0) return null;
  const [[xa, ya], [xb, yb], [, zb], [, za]] = layer.poly as Pt[];
  const pts = `${xa},${ya} ${xb},${yb} ${xb},${yb + (zb - yb) * p} ${xa},${ya + (za - ya) * p}`;
  const id = `slice-${layer.owner}-${Math.round(xa)}-${Math.round(ya)}`;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      <defs>
        <clipPath id={id}><polygon points={pts} /></clipPath>
      </defs>
      <SvgPhoto photo={{...(layer.photo as Photo), crop: [0, 0, 1]}} box={layer.place as Box} clip={id} />
    </svg>
  );
};

/** Bars: flat bars of the `color`, [x, y, w, h] px each, drawn out from their left ends, one every `step` beats from `at`. */
export const Bars: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {W, H} = useSafe();
  const dur = Math.max(1, Math.round(L.pulse * (layer.beats ?? 0.5)));
  const step = L.pulse * (layer.step ?? 0.1);
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
      {(layer.bars as Box[]).map(([x, y, w, h], i) => {
        const p = L.tween(0, 1, L.start + Math.round(i * step), dur, 'enter');
        return p > 0 ? <rect key={i} x={x} y={y} width={w * p} height={h} fill={color(layer.color ?? 'ink')} /> : null;
      })}
    </svg>
  );
};

/* ---------------------------------------------------------------- film: the twine */

/** A path through orthogonal points with every corner rounded to `r` px, and its length. */
const roundPath = (pts: Pt[], r: number) => {
  let d = `M${pts[0][0]},${pts[0][1]}`;
  let len = 0;
  for (let i = 1; i < pts.length; i++) {
    const [px, py] = pts[i - 1];
    const [cx, cy] = pts[i];
    const seg = Math.hypot(cx - px, cy - py);
    if (i < pts.length - 1) {
      const [nx, ny] = pts[i + 1];
      const next = Math.hypot(nx - cx, ny - cy);
      const rr = Math.min(r, seg / 2, next / 2);
      const a: Pt = [cx - ((cx - px) / seg) * rr, cy - ((cy - py) / seg) * rr];
      const b: Pt = [cx + ((nx - cx) / next) * rr, cy + ((ny - cy) / next) * rr];
      d += ` L${a[0].toFixed(1)},${a[1].toFixed(1)} Q${cx},${cy} ${b[0].toFixed(1)},${b[1].toFixed(1)}`;
      len += seg - rr * (i > 1 ? 2 : 1) + rr * 1.57;
    } else {
      d += ` L${cx},${cy}`;
      len += seg;
    }
  }
  return {d, len: len + r};
};

/** A bow of baker's twine centred on `at`, `s` times its size. */
const Bow: React.FC<{at: Pt; s: number; color: string}> = ({at, s, color}) => (
  <g transform={`translate(${at[0]} ${at[1]}) scale(${s})`}>
    <ellipse cx={-5} cy={-3} rx={7} ry={4.5} transform="rotate(-30 -5 -3)" fill="none" stroke={color} strokeWidth={3.2} />
    <ellipse cx={5} cy={-3} rx={7} ry={4.5} transform="rotate(30 5 -3)" fill="none" stroke={color} strokeWidth={3.2} />
    <circle r={3.6} fill={color} />
  </g>
);

/**
 * YearRule: the year as a line from `x0` to `x1` at `y` (px), months marked above it (`months`: [{x, label}]), the
 * days the nine were posted as knots tied on it (`knots`: [{x, at}] each at its own musical beat), drawn left to right over
 * `beats`, so the twine hangs from the line into the space below with nothing written there. With
 * `next` {x, label} the rule runs on past december into the next year, dashed, with the label over it, drawn over
 * `nextBeats` from `nextAt` (or as soon as the rule is drawn).
 */
export const YearRule: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {system} = useSys();
  const {W, H} = useSafe();
  const ref = useRef<SVGSVGElement>(null);
  const {x0, x1, y} = layer as unknown as {x0: number; x1: number; y: number};
  const dur = Math.max(1, Math.round(L.pulse * (layer.beats ?? 1)));
  const p = L.tween(0, 1, L.start, dur, 'move');
  const ink = color(layer.color ?? 'ink');
  const twine = color(layer.twine ?? 'accent');
  const next = layer.next as {x: number; label: string; size?: number} | undefined;
  const np = next ? L.tween(0, 1, layer.nextAt !== undefined ? L.at(layer.nextAt) : L.start + dur, Math.round(L.pulse * (layer.nextBeats ?? 1)), 'move') : 0;
  const ls: number = layer.labelSize ?? 22;
  useSafeCheck(ref, p >= 1);
  return (
    <svg ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      <line x1={x0} y1={y} x2={x0 + (x1 - x0) * p} y2={y} stroke={ink} strokeWidth={3} />
      {(layer.months as {x: number; label: string}[]).map((m, i) => {
        const on = L.tween(0, 1, L.start + dur * ((m.x - x0) / (x1 - x0)), 6, 'enter');
        return (
          <g key={i} opacity={on}>
            <line x1={m.x} y1={y - 8} x2={m.x} y2={y + 4} stroke={ink} strokeWidth={2} />
            <text x={m.x + 5} y={y - 14} fill={ink} style={lineStyle(system.text, {text: '', x: 0, y: 0, size: ls, weight: 500, tracking: 0.02})} data-name={`month-${m.label}`}>
              {m.label}
            </text>
          </g>
        );
      })}
      {next ? (
        <g opacity={np > 0 ? 1 : 0}>
          <line x1={x1} y1={y} x2={x1 + (next.x - x1) * np} y2={y} stroke={ink} strokeWidth={3} strokeDasharray="10 8" />
          <text x={x1 + 8} y={y - 14} fill={ink} opacity={np}
            style={lineStyle(system.text, {text: '', x: 0, y: 0, size: ls, weight: 700, tracking: 0.02})} data-name="rule-next">
            {next.label}
          </text>
        </g>
      ) : null}
      {(layer.knots as {x: number; at: number}[]).map((k, i) =>
        L.frame >= L.at(k.at) ? <Bow key={i} at={[k.x, y]} s={L.hit(L.at(k.at))} color={twine} /> : null,
      )}
    </svg>
  );
};

/**
 * Twine: baker's twine, red with the white strand showing in short flecks along its twist, run along `points` (px, orthogonal, corners rounded) from a post's day on the rule
 * to its square on the wall, drawn on over `beats` from `at`. From `lightAt` it sits at a light tint while another
 * strand is tied, and from `fullAt` it comes back to full red (both in musical beats of the beat).
 */
export const Twine: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {W, H} = useSafe();
  const {d, len} = roundPath(layer.points as Pt[], layer.radius ?? 18);
  const dur = Math.max(1, Math.round(L.pulse * (layer.beats ?? 1)));
  const p = L.tween(0, 1, L.start, dur, 'move');
  const red = color(layer.color ?? 'accent');
  const wd: number = layer.width ?? 5;
  const id = `tw-${layer.id}`;
  const fade = Math.round(L.pulse * 0.5);
  const light = layer.lightAt !== undefined ? L.tween(0, 1, L.at(layer.lightAt), fade, 'move') : 0;
  const full = layer.fullAt !== undefined ? L.tween(0, 1, L.at(layer.fullAt), fade, 'move') : 0;
  if (p <= 0) return null;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible', opacity: 1 - 0.68 * Math.max(0, light - full)}}>
      <defs>
        <mask id={id} maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
          <path d={d} fill="none" stroke="#fff" strokeWidth={wd + 6} strokeDasharray={`${len * p} ${len * 2}`} strokeLinecap="round" />
        </mask>
      </defs>
      <g mask={`url(#${id})`}>
        <path d={d} fill="none" stroke="#000" strokeOpacity={0.14} strokeWidth={wd + 2} transform="translate(1.5 2.5)" />
        <path d={d} fill="none" stroke={red} strokeWidth={wd} strokeLinecap="round" />
        <path d={d} fill="none" stroke="#fbf7f0" strokeWidth={wd * 0.55} strokeDasharray={`${wd * 0.45} ${wd * 1.25}`} />
      </g>
    </svg>
  );
};

/**
 * Tile: one square of the wall at `box` (px), its photograph by its decided crop, dropped in over `beats` from `at`.
 * `paper` px of border in the paper color.
 */
export const Tile: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {W, H} = useSafe();
  const [x, y, w, h] = layer.box as Box;
  const dur = Math.max(1, Math.round(L.pulse * (layer.beats ?? 0.5)));
  const p = L.tween(0, 1, L.start, dur, 'enter');
  if (p <= 0 && !layer.empty) return null;
  const s = 0.94 + 0.06 * p;
  const cx = x + w / 2;
  const cy = y + h / 2;
  return (
    <svg width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      {layer.empty ? (
        <rect x={x + 1.5} y={y + 1.5} width={w - 3} height={h - 3} fill="none" stroke={color(layer.emptyColor ?? 'muted')} strokeWidth={2} strokeDasharray="2 8" strokeLinecap="round" />
      ) : null}
      {p > 0 ? (
        <g opacity={Math.min(1, p * 1.6)} transform={`translate(${cx} ${cy}) scale(${s}) translate(${-cx} ${-cy})`}>
          <rect x={x} y={y + 8} width={w} height={h} fill="#000" opacity={0.12 * p} />
          <SvgPhoto photo={layer.photo as Photo} box={[x, y, w, h]} />
        </g>
      ) : null}
    </svg>
  );
};

/**
 * Tag: a paper tag tied on the twine by its hole at `pos` (px), the hole in its left end (`hole` left) or its top edge
 * (`hole` top), `w` x `h` px, turned `rotate` degrees about the hole, carrying `lines` (positions relative to the tag's
 * top-left). It swings in on the hit spring at `at`, and the twine is tied through its hole in a bow `h / 60` times
 * the rule's.
 */
export const Tag: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const faces = useFaces();
  const {W, H} = useSafe();
  const ref = useRef<SVGSVGElement>(null);
  const [px, py] = layer.pos as Pt;
  const w: number = layer.w ?? 120;
  const h: number = layer.h ?? 64;
  const s = L.hit(L.start);
  const rot = (layer.rotate ?? 0) + (1 - s) * 18;
  const paper = color(layer.paper ?? 'paper');
  const ch = Math.min(16, h * 0.25, w * 0.12);
  const top = layer.hole === 'top';
  const [hx, hy] = top ? [w / 2, ch * 0.95] : [ch * 0.95, h / 2];
  useSafeCheck(ref, L.frame >= L.start + L.pulse * 2);
  if (L.frame < L.start) return null;
  const shape = top ? `M0,${ch} L${ch},0 L${w - ch},0 L${w},${ch} L${w},${h} L0,${h} Z` : `M${ch},0 L${w},0 L${w},${h} L${ch},${h} L0,${h - ch} L0,${ch} Z`;
  return (
    <svg ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      <g transform={`translate(${px} ${py}) rotate(${rot}) scale(${Math.min(1.08, 0.6 + 0.4 * s)}) translate(${-hx} ${-hy})`}>
        <path d={shape} fill="#000" opacity={0.18} transform="translate(3 5)" />
        <path d={shape} fill={paper} stroke={tint(color('ink'), 0.22)} strokeWidth={1.5} />
        <circle cx={hx} cy={hy} r={5} fill={color('bg')} stroke={tint(color('ink'), 0.45)} strokeWidth={2} />
        {(layer.lines as Line[]).map((ln, i) => (
          <text key={i} x={ln.x} y={ln.y} textAnchor={ln.anchor ?? 'start'} fill={color(ln.color ?? 'ink')} style={lineStyle(faces(ln.face), ln)}
            data-name={ln.name ?? `tag-${ln.text}`}>
            {ln.text}
          </text>
        ))}
      </g>
      <Bow at={[px, py]} s={(h / 60) * Math.min(1, s)} color={color(layer.twine ?? 'accent')} />
    </svg>
  );
};

/* ---------------------------------------------------------------- calm: the tubs */

/** A strip of masking tape from `x` to `x + w` centred on `y`, `h` px tall, turned `rot` degrees, torn at both ends. */
const TapeStrip: React.FC<{x: number; y: number; w: number; h: number; rot?: number; fill: string; seed?: number}> = ({x, y, w, h, rot = 0, fill, seed = 1}) => {
  const tear = (k: number) => [0, 0.25, 0.5, 0.75, 1].map((t, i) => [((Math.sin(seed * 7.1 + i * 3.3 + k) + 1) / 2) * 5, t * h] as Pt);
  const left = tear(1).map(([dx, dy]) => `${x + dx},${y - h / 2 + dy}`);
  const right = tear(2).reverse().map(([dx, dy]) => `${x + w - dx},${y - h / 2 + dy}`);
  return (
    <g transform={`rotate(${rot} ${x + w / 2} ${y})`}>
      <polygon points={[...left, ...right].join(' ')} fill="#000" opacity={0.12} transform="translate(1.5 2.5)" />
      <polygon points={[...left, ...right].join(' ')} fill={fill} opacity={0.94} />
    </g>
  );
};

/**
 * Tub: a clear proofing tub at `box` (px) in which a post rises from the bottom to `level` (its likes over the
 * tub's full mark), over a time proportional to the height (`beatsPerFull` musical beats for the whole tub) from `at`,
 * the top of the photograph domed like dough. The risen part shows the photograph cropped around its focus, so a low
 * rise shows the post's subject, never only the edge of the picture under it. The graduations on its side are quarters
 * of the full mark (`ticks` labelled when `tickLabels`). When the rise stops, a strip of tape is pressed on at the level carrying `tape` lines. With `full`
 * the post goes on rising to the top after `fullAt`, and the tape stays where it was.
 */
export const Tub: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const faces = useFaces();
  const {system} = useSys();
  const {W, H} = useSafe();
  const ref = useRef<SVGSVGElement>(null);
  const [x, y, w, h] = layer.box as Box;
  const level: number = layer.level ?? 1;
  const wall: number = layer.wall ?? Math.max(6, w * 0.028);
  const ix = x + wall;
  const iw = w - 2 * wall;
  const top = y + h * 0.045;
  const ih = y + h - wall - top;
  const riseFrames = Math.max(1, Math.round(L.pulse * (layer.beatsPerFull ?? 16) * level));
  const lv = L.tween(0, level, L.start, riseFrames, 'move');
  const fullAt = layer.fullAt !== undefined ? L.at(layer.fullAt) : null;
  const fv = fullAt !== null ? L.tween(0, 1, fullAt, Math.round(L.pulse * (layer.fullBeats ?? 2)), 'move') : 0;
  const shown = lv + (1 - level) * fv;
  const dome = Math.min(iw * 0.07, ih * shown * 0.5) * (1 - fv * 0.85);
  const bandTop = top + ih * (1 - shown);
  const ink = color(layer.ink ?? 'ink');
  const id = `tub-${layer.id}`;
  const stopped = L.frame >= L.start + riseFrames;
  const tp = L.hit(L.start + riseFrames + Math.round(L.pulse * 0.25));
  const tapeY = top + ih * (1 - level);
  const tapeH: number = layer.tapeH ?? Math.max(30, w * 0.13);
  const tapeLines = (layer.tape ?? []) as Line[];
  const tickLabels = (layer.tickLabels ?? []) as string[];
  const tickSize: number = layer.tickSize ?? Math.max(13, w * 0.045);
  useSafeCheck(ref, stopped && L.frame >= L.start + riseFrames + L.pulse);
  return (
    <svg ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      <defs>
        <clipPath id={`${id}-in`}>
          <rect x={ix} y={top} width={iw} height={ih} rx={w * 0.05} />
        </clipPath>
        <clipPath id={`${id}-band`}>
          <path d={`M${ix},${top + ih} L${ix},${bandTop + dome} Q${ix + iw / 2},${bandTop - dome} ${ix + iw},${bandTop + dome} L${ix + iw},${top + ih} Z`} />
        </clipPath>
        <linearGradient id={`${id}-glass`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#fff" stopOpacity={0.5} />
          <stop offset="0.12" stopColor="#fff" stopOpacity={0.08} />
          <stop offset="0.85" stopColor="#fff" stopOpacity={0.04} />
          <stop offset="1" stopColor="#fff" stopOpacity={0.35} />
        </linearGradient>
      </defs>
      <rect x={x} y={y + h * 0.02} width={w} height={h * 0.98} rx={w * 0.07} fill="#000" opacity={0.07} transform="translate(0 10)" />
      <rect x={x} y={y + h * 0.02} width={w} height={h * 0.98} rx={w * 0.07} fill={tint(color('paper'), 0.55)} />
      <g clipPath={`url(#${id}-in)`}>
        {shown > 0.001 ? (
          <g clipPath={`url(#${id}-band)`}>
            <SvgPhoto photo={{...(layer.photo as Photo), crop: undefined}} box={[ix, bandTop - dome, iw, top + ih - bandTop + dome]} clip={`${id}-in`} />
          </g>
        ) : null}
      </g>
      <rect x={x} y={y + h * 0.02} width={w} height={h * 0.98} rx={w * 0.07} fill={`url(#${id}-glass)`} />
      <rect x={x + wall * 0.5} y={y + h * 0.02} width={w - wall} height={h * 0.98 - wall * 0.5} rx={w * 0.065} fill="none" stroke={tint(ink, 0.55)} strokeWidth={Math.max(2, wall * 0.35)} />
      <rect x={x - wall * 0.4} y={y} width={w + wall * 0.8} height={Math.max(8, h * 0.035)} rx={4} fill={tint(ink, 0.18)} stroke={tint(ink, 0.5)} strokeWidth={1.5} />
      {[0.25, 0.5, 0.75, 1].map((q, i) => {
        const ty = top + ih * (1 - q);
        return (
          <g key={q}>
            <line x1={ix + 2} y1={ty} x2={ix + 2 + (q === 1 ? iw * 0.16 : iw * 0.09)} y2={ty} stroke={ink} strokeOpacity={0.75} strokeWidth={2} />
            {[1, 2, 3, 4].map((m) => {
              const my = top + ih * (1 - q + m * 0.05);
              return m < 5 && q - m * 0.05 > 0 ? <line key={m} x1={ix + 2} y1={my} x2={ix + 2 + iw * 0.04} y2={my} stroke={ink} strokeOpacity={0.45} strokeWidth={1.5} /> : null;
            })}
            {tickLabels[i] ? (
              <text x={ix + 6 + iw * 0.16} y={ty + tickSize * 0.36} fill={ink} fillOpacity={0.85}
                style={lineStyle(system.text, {text: '', x: 0, y: 0, size: tickSize, weight: 500})} data-name={`tick-${layer.id}-${q}`}>
                {tickLabels[i]}
              </text>
            ) : null}
          </g>
        );
      })}
      {stopped && tp > 0 ? (
        <g transform={`translate(0 ${(1 - Math.min(1, tp)) * -16})`} opacity={Math.min(1, tp * 1.5)}>
          <TapeStrip x={layer.tapeX ?? ix + iw * 0.3} y={tapeY - tapeH / 2 + 3} w={layer.tapeW ?? iw * 0.74} h={tapeH} rot={layer.tapeRot ?? -1.5}
            fill={color(layer.tapeColor ?? 'accent2')} seed={layer.rank ?? 1} />
          {tapeLines.map((ln, i) => (
            <text key={i} x={ln.x} y={ln.y} textAnchor={ln.anchor ?? 'start'} fill={color(ln.color ?? 'ink')} style={lineStyle(faces(ln.face), ln)}
              transform={`rotate(${layer.tapeRot ?? -1.5} ${ln.x} ${ln.y})`} data-name={ln.name ?? `tape-${ln.text}`}>
              {ln.text}
            </text>
          ))}
        </g>
      ) : null}
    </svg>
  );
};

/**
 * Scale: the tubs' graduations read once for a row of tubs, at the wall's left edge: for each row (`rows`: [{bottom,
 * top}] px of the tubs' inner height) a tick at every quarter and the label right-aligned at `x`, `size` px, fading in
 * from `at`.
 */
export const Scale: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {system} = useSys();
  const {W, H} = useSafe();
  const ref = useRef<SVGSVGElement>(null);
  const x: number = layer.x;
  const size: number = layer.size ?? 34;
  const labels = (layer.labels ?? []) as string[];
  const ink = color(layer.ink ?? 'ink');
  const on = L.tween(0, 1, L.start, Math.round(L.pulse * (layer.beats ?? 0.5)), 'enter');
  useSafeCheck(ref, on >= 1);
  return (
    <svg ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible', opacity: on}}>
      {(layer.rows as {bottom: number; top: number}[]).map((r, i) =>
        [0.25, 0.5, 0.75, 1].map((q, j) => {
          const y = r.bottom + (r.top - r.bottom) * q;
          return (
            <g key={`${i}-${j}`}>
              <line x1={x + 8} y1={y} x2={x + 22} y2={y} stroke={ink} strokeWidth={2.5} />
              <text x={x} y={y + size * 0.36} textAnchor="end" fill={ink}
                style={lineStyle(system.text, {text: '', x: 0, y: 0, size, weight: 500})} data-name={`scale-${i}-${labels[j]}`}>
                {labels[j]}
              </text>
            </g>
          );
        }),
      )}
    </svg>
  );
};

/**
 * Tape: a strip of masking tape across the composition at `x`, `y` (px, the strip's left end and centre line), `w` x
 * `h`, turned `rot` degrees, carrying `lines` (px, absolute), pressed on with the hit spring at `at`.
 */
export const Tape: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const faces = useFaces();
  const {W, H} = useSafe();
  const ref = useRef<SVGSVGElement>(null);
  const s = L.hit(L.start);
  const rot: number = layer.rot ?? 0;
  const cx = layer.x + layer.w / 2;
  useSafeCheck(ref, L.frame >= L.start + L.pulse * 2);
  if (L.frame < L.start) return null;
  return (
    <svg ref={ref} width={W} height={H} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      <g transform={`translate(${cx} ${layer.y}) scale(${0.85 + 0.15 * Math.min(1.1, s)}) translate(${-cx} ${-layer.y})`} opacity={Math.min(1, s * 1.5)}>
        <TapeStrip x={layer.x} y={layer.y} w={layer.w} h={layer.h ?? 56} rot={rot} fill={color(layer.color ?? 'accent2')} seed={layer.seed ?? 3} />
        {(layer.lines as Line[]).map((ln, i) => (
          <text key={i} x={ln.x} y={ln.y} textAnchor={ln.anchor ?? 'start'} fill={color(ln.color ?? 'ink')} style={lineStyle(faces(ln.face), ln)}
            transform={`rotate(${rot} ${cx} ${layer.y})`} data-name={ln.name ?? `tape-${ln.text}`}>
            {ln.text}
          </text>
        ))}
      </g>
    </svg>
  );
};
