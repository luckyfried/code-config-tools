import {fitTextOnNLines} from '@remotion/layout-utils';
import React from 'react';
import {AbsoluteFill, Img, interpolate, random} from 'remotion';
import {Box, LivePhoto, Photo, pick, Print, RETRIES, useBox, useLayer} from './layer';
import {faceStyle, hash, src, tint, useColor, useMotion, useSafe, useSys} from './system';
import {Mark, Marks, PhotoIn} from './marks';
import {SafeBox} from './text';
import type {Clip, Layer} from './types';

type P = {layer: Layer};

const clamp01 = (v: number) => Math.max(0, Math.min(1, v));

/** The camera shake of a landing: a short decaying jolt after each arrival. */
const jolt = (frame: number, at: number[], amp: number) =>
  at.reduce((s, a) => {
    const t = frame - a;
    return t < 0 || t > 14 ? s : s + amp * Math.exp(-t / 3.5) * Math.sin(t * 1.9);
  }, 0);

/**
 * Slam: each photo lands on a beat at 1.15 to 1.0 on the hit spring, a thin paper frame and a shadow; the stack
 * grows one print per arrival, the frame jolts on every landing, and the stack keeps drifting and turning between them.
 */
export const Slam: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const photos: string[] = layer.photos ?? (layer.photo ? [layer.photo] : []);
  const n = layer.count ?? photos.length;
  const arr = L.arrivals(n, layer.every ?? 1);
  const b = useBox(layer.box, [0.1, 0.15, 0.8, 0.5]);
  const shake = jolt(L.frame, arr, layer.jolt ?? 9);
  const gone = L.leave(Math.round(L.pulse * 0.6));
  const landed = arr.filter((a) => L.frame >= a).length;
  return (
    <AbsoluteFill style={{transformOrigin: `${(b.left + b.width / 2) / b.W * 100}% ${(b.top + b.height / 2) / b.H * 100}%`,
      transform: `translate(${shake}px, ${shake * -0.6}px) translate(${L.drift(-3, 3)}%, ${L.drift(2, -2)}%) scale(${L.travel(1, 1.08)}) translateY(${-gone * 130}%) rotate(${gone * -6 + L.travel(-1.2, 1.2)}deg)`}}>
      {arr.map((a, k) => {
        if (L.frame < a || k < landed - 3) return null;
        const p = L.hit(a);
        const rot = (hash(`${layer.id ?? ''}${k}`) - 0.5) * (layer.tilt ?? 7);
        const dx = (hash(`x${k}${photos.length}`) - 0.5) * 0.06 * b.W;
        const dy = (hash(`y${k}${photos.length}`) - 0.5) * 0.04 * b.H;
        const under = landed - 1 - k;
        return (
          <div
            key={k}
            style={{
              position: 'absolute',
              left: b.left + dx,
              top: b.top + dy,
              width: b.width,
              height: b.height,
              transform: `scale(${1.15 - 0.15 * p}) rotate(${rot * (0.6 + 0.4 * p)}deg)`,
              opacity: clamp01((L.frame - a + 1) / 2),
              filter: under > 0 ? `brightness(${1 - 0.18 * under})` : undefined,
            }}
          >
            <Print file={pick(photos, k)} border={layer.border ?? 4} shadow={0.25 + 0.3 * p} pos={layer.pos} />
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const gridRects = (n: number, b: {left: number; top: number; width: number; height: number}, gap: number) => {
  const {left: x, top: y, width: w, height: h} = b;
  if (n <= 2) return [[x, y, w, (h - gap) / 2], [x, y + (h + gap) / 2, w, (h - gap) / 2]];
  if (n === 3) {
    const top = (h - gap) * 0.58;
    const bw = (w - gap) / 2;
    return [[x, y, w, top], [x, y + top + gap, bw, h - top - gap], [x + bw + gap, y + top + gap, bw, h - top - gap]];
  }
  const cw = (w - gap) / 2;
  const ch = (h - gap) / 2;
  return [[x, y, cw, ch], [x + cw + gap, y, cw, ch], [x, y + ch + gap, cw, ch], [x + cw + gap, y + ch + gap, cw, ch]];
};

/**
 * MultiFrame: two to four photos in a grid, each arriving on consecutive beats through a wipe from its own side,
 * the grid lines drawn in first. In the last beat the camera pushes into the `focus` tile; when the next beat cuts in
 * on `match`, the focus tile grows to the full frame on the cut, so the next beat carries the same photo on.
 */
export const MultiFrame: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {exit} = useSys();
  const color = useColor();
  const photos: string[] = (layer.photos ?? []).slice(0, 4);
  const b = useBox(layer.box, [0.06, 0.13, 0.88, 0.6]);
  const gap = layer.gap ?? 16;
  const rects = gridRects(photos.length, b, gap);
  const arr = L.arrivals(photos.length, layer.every ?? 1);
  const focus = Math.min(layer.focus ?? 0, photos.length - 1);
  const lines = L.tween(0, 1, L.start, Math.round(L.pulse * 1.2), 'move');
  const n = exit?.preset === 'match' ? exit.frames ?? 8 : 0;
  const grow = n ? L.tween(0, 1, L.duration - n, n, 'move') : 0;
  const push = L.tween(0, 1, L.duration - L.pulse - n, L.pulse + n, 'move');
  const [fx, fy, fw, fh] = rects[focus];
  const ox = fx + fw / 2;
  const oy = fy + fh / 2;
  const sides = ['inset(0 100% 0 0)', 'inset(0 0 0 100%)', 'inset(100% 0 0 0)', 'inset(0 0 100% 0)'];
  const rule = color(layer.rule ?? 'paper');
  return (
    <AbsoluteFill style={{transformOrigin: `${ox}px ${oy}px`, transform: `scale(${1 + (L.travel(0, 0.05) + push * 0.08) * (1 - grow)}) rotate(${L.travel(-0.8, 0.8) * (1 - grow)}deg)`}}>
      {rects.map(([x, y, w, h], k) => {
        const p = L.tween(0, 1, arr[k], Math.round(L.pulse * 0.7), 'enter');
        const q = L.pop(arr[k]);
        const isF = k === focus;
        const r = isF ? grow : 0;
        const X = interpolate(r, [0, 1], [x, 0]);
        const Y = interpolate(r, [0, 1], [y, 0]);
        const Wd = interpolate(r, [0, 1], [w, b.W]);
        const Hd = interpolate(r, [0, 1], [h, b.H]);
        const reveal = p >= 1 ? 'none' : sides[k % 4].replace('100%', `${(1 - p) * 100}%`);
        return (
          <div
            key={k}
            style={{
              position: 'absolute',
              left: X,
              top: Y,
              width: Wd,
              height: Hd,
              overflow: 'hidden',
              clipPath: reveal,
              opacity: isF ? 1 : 1 - grow,
              zIndex: isF ? 2 : 1,
            }}
          >
            <AbsoluteFill style={{transform: `scale(${interpolate(r, [0, 1], [1.25 - 0.15 * q + L.travel(0, 0.1), 1])}) ` +
              `translate${k % 2 ? 'X' : 'Y'}(${interpolate(r, [0, 1], [L.travel(k % 3 ? 4 : -4, k % 3 ? -4 : 4), 0])}%)`}}>
              <Photo file={photos[k]} pos={layer.pos} />
            </AbsoluteFill>
          </div>
        );
      })}
      <svg width={b.W} height={b.H} style={{position: 'absolute', inset: 0, opacity: 1 - grow, zIndex: 3}}>
        {rects.map(([x, y, w, h], k) => (
          <rect
            key={k}
            x={x - gap / 2}
            y={y - gap / 2}
            width={w + gap}
            height={h + gap}
            fill="none"
            stroke={rule}
            strokeWidth={Math.max(2, gap * 0.35)}
            pathLength={1}
            strokeDasharray={1}
            strokeDashoffset={1 - clamp01(lines * 1.4 - k * 0.15)}
          />
        ))}
        <line x1={b.left - 40} x2={b.left + b.width + 40} y1={b.top - gap * 2} y2={b.top - gap * 2} stroke={color('accent')} strokeWidth={4}
          pathLength={1} strokeDasharray={1} strokeDashoffset={1 - lines} />
        <line x1={b.left - 40} x2={b.left + b.width + 40} y1={b.top + b.height + gap * 2} y2={b.top + b.height + gap * 2} stroke={color('accent')}
          strokeWidth={4} pathLength={1} strokeDasharray={1} strokeDashoffset={-(1 - lines)} />
      </svg>
    </AbsoluteFill>
  );
};

/**
 * MaskReveal: the photo seen through a moving shape in the palette.
 * circle  a palette disk lands with the photo already inside it, the photo opens to its ring, and the circle keeps
 *         growing; `open` takes it to the full frame
 * bars    palette bars drop in a stagger and the photo follows in each, every bar drifting at its own speed
 * word    the photo seen through the letters of a word cut from a palette field; `open` flies through a letter to the full frame
 */
export const MaskReveal: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system} = useSys();
  const color = useColor();
  const {W, H} = useSafe();
  const file: string = layer.photo ?? pick(layer.photos, 0);
  const fill = color(layer.color ?? 'accent');
  const shape: string = layer.shape ?? 'circle';
  const openAt = layer.open === undefined ? null : L.start + Math.round(layer.open * L.pulse);
  const open = openAt === null ? 0 : L.tween(0, 1, openAt, Math.round(L.pulse * 1.2), 'exit');
  const [ox, oy] = layer.origin ?? [0.5, 0.42];
  if (shape === 'bars') {
    const n = layer.count ?? 5;
    const bw = W / n;
    return (
      <AbsoluteFill>
        {Array.from({length: n}, (_, k) => {
          const a = L.start + k * Math.max(2, L.stagger);
          const c = L.tween(0, 1, a, Math.round(L.pulse * 0.6), 'enter');
          const p = L.tween(0, 1, a + Math.round(L.pulse * 0.35), Math.round(L.pulse * 0.7), 'enter');
          const down = k % 2 === 0;
          const sway = L.travel(down ? 18 : -18, down ? -18 : 18) * (0.7 + 0.3 * ((k * 7) % 3) / 2);
          return (
            <div key={k} style={{position: 'absolute', left: k * bw - 0.5, width: bw + 1, top: 0, height: H, overflow: 'hidden'}}>
              <div style={{position: 'absolute', inset: 0, background: k % 2 ? color('accent2') : fill, transformOrigin: down ? '50% 0%' : '50% 100%', transform: `scaleY(${c})`}} />
              <div style={{position: 'absolute', inset: 0, overflow: 'hidden', clipPath: `inset(${down ? 0 : (1 - p) * 100}% 0 ${down ? (1 - p) * 100 : 0}% 0)`}}>
                <div style={{position: 'absolute', top: '-30%', height: '160%', left: -k * bw, width: W, transform: `translateY(${sway}%) scale(${L.travel(1.3, 1.04)})`}}>
                  <Photo file={file} pos={layer.pos} />
                </div>
              </div>
            </div>
          );
        })}
      </AbsoluteFill>
    );
  }
  if (shape === 'word') {
    const word: string = String(layer.word ?? '').toUpperCase();
    const f = system.display;
    const size = layer.size ?? Math.min(system.scale.hero * 1.5, (W * 1.7) / Math.max(1, word.length));
    const s = L.pop(L.start);
    const k = interpolate(open, [0, 1], [0, 1], {easing: (t) => t * t * t});
    const scale = (0.86 + 0.14 * s + L.travel(0, 0.1)) * (1 + k * 40);
    const tr = interpolate(s, [0, 1], [0.5, Math.max(-0.02, f.tracking)]);
    return (
      <AbsoluteFill>
        <LivePhoto file={file} pos={layer.pos} from={1.18 - open * 0.1} to={1.06} dx={1.5} dy={1} />
        <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: 1 - clamp01((open - 0.85) / 0.15)}}>
          <defs>
            <mask id={`word-${layer.id ?? 'm'}`} maskUnits="userSpaceOnUse" x={0} y={0} width={W} height={H}>
              <rect x={0} y={0} width={W} height={H} fill="white" />
              <text
                x={W * ox}
                y={H * oy}
                textAnchor="middle"
                dominantBaseline="central"
                fill="black"
                style={{fontFamily: `'${f.family}'`, fontWeight: f.weight, letterSpacing: `${tr}em`, fontSize: size}}
                transform={`translate(${W * ox} ${H * oy}) scale(${scale}) translate(${-W * ox} ${-H * oy})`}
              >
                {word}
              </text>
            </mask>
          </defs>
          <rect x={0} y={0} width={W} height={H} fill={fill} mask={`url(#word-${layer.id ?? 'm'})`} />
        </svg>
      </AbsoluteFill>
    );
  }
  const r0 = layer.radius ?? 0.34;
  const disk = L.hit(L.start - 3);
  const p = Math.max(L.pop(L.start + Math.round(L.pulse * 0.5)), 0.55 * disk);
  const r = (r0 * p + L.travel(0, 0.06)) * W + open * H * 1.2;
  const ring = r + 18 + 10 * (1 - p);
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: W * ox - r0 * W * disk - 30, top: H * oy - r0 * W * disk - 30, width: (r0 * W * disk + 30) * 2,
        height: (r0 * W * disk + 30) * 2, borderRadius: '50%', background: fill, opacity: 1 - open}} />
      <AbsoluteFill style={{clipPath: `circle(${Math.max(0, r)}px at ${ox * 100}% ${oy * 100}%)`}}>
        <LivePhoto file={file} pos={layer.pos} from={1.2} to={1.06} dx={-1.5} dy={1} />
      </AbsoluteFill>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0, opacity: (1 - open) * p}}>
        <circle cx={W * ox} cy={H * oy} r={ring} fill="none" stroke={color('paper')} strokeWidth={5} strokeDasharray="4 22"
          transform={`rotate(${L.travel(0, 70)} ${W * ox} ${H * oy})`} />
      </svg>
    </AbsoluteFill>
  );
};

/**
 * Split: the frame cut into two or three panels of the same or different photos, each sliding in from the opposite
 * end and then travelling against its neighbour, a palette rule drawn between them.
 */
export const Split: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const color = useColor();
  const {W, H} = useSafe();
  const photos: string[] = layer.photos ?? [layer.photo];
  const n = Math.max(2, Math.min(3, layer.panels ?? photos.length));
  const cols = (layer.orient ?? 'v') === 'v';
  const arr = L.arrivals(n, layer.every ?? 0.5);
  const size = (cols ? W : H) / n;
  const ruleP = L.tween(0, 1, arr[n - 1], Math.round(L.pulse), 'enter');
  const rw = layer.rule ?? 6;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      {Array.from({length: n}, (_, k) => {
        const p = L.pop(arr[k]);
        const sign = k % 2 === 0 ? -1 : 1;
        const slide = (1 - p) * 105 * sign;
        const drift = L.travel(sign * 9, -sign * 9);
        const one = photos.length === 1;
        const box: React.CSSProperties = cols
          ? {left: k * size, top: 0, width: size + 1, height: H}
          : {left: 0, top: k * size, width: W, height: size + 1};
        const inner: React.CSSProperties = cols
          ? {left: one ? -k * size : 0, width: one ? W : size, top: '-14%', height: '128%'}
          : {top: one ? -k * size : 0, height: one ? H : size, left: '-14%', width: '128%'};
        return (
          <div key={k} style={{position: 'absolute', ...box, overflow: 'hidden', transform: cols ? `translateY(${slide}%)` : `translateX(${slide}%)`}}>
            <div style={{position: 'absolute', ...inner, transform: cols ? `translateY(${drift}%)` : `translateX(${drift}%)`}}>
              <Photo file={pick(photos, k)} pos={layer.pos} style={{transform: `scale(${L.travel(1.1, 1.18)})`}} />
            </div>
          </div>
        );
      })}
      {Array.from({length: n - 1}, (_, k) => (
        <div
          key={`r${k}`}
          style={{
            position: 'absolute',
            background: color(layer.color ?? 'accent'),
            ...(cols
              ? {left: (k + 1) * size - rw / 2, width: rw, top: 0, height: H, transformOrigin: k % 2 ? '50% 100%' : '50% 0%', transform: `scaleY(${ruleP})`}
              : {top: (k + 1) * size - rw / 2, height: rw, left: 0, width: W, transformOrigin: k % 2 ? '100% 50%' : '0% 50%', transform: `scaleX(${ruleP})`}),
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

/**
 * Parallax: the photo in planes moving at their own speed and scale, with its title between them. With a cutout
 * (from grade.py cutout) the subject floats over its own background; without one the back plane is a blurred
 * duplicate and the sharp photo rides in front of the title in a window.
 */
export const Parallax: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system, enter} = useSys();
  const color = useColor();
  const {W, H} = useSafe();
  const file: string = layer.photo ?? pick(layer.photos, 0);
  const matched = enter?.preset === 'match';
  const blur = L.tween(0, layer.blur ?? 14, L.start + (matched ? Math.round(L.pulse) : 0), Math.round(L.pulse * 1.5), 'move');
  const back = (
    <AbsoluteFill style={{transform: `scale(${L.travel(1.04, 1.3)}) translate(${L.travel(2, -2)}%, ${L.travel(2, -5)}%)`, filter: layer.cutout ? undefined : `blur(${blur}px) brightness(${1 - blur / 50})`}}>
      <Photo file={file} pos={layer.pos} />
    </AbsoluteFill>
  );
  const f = system.display;
  const title: string = layer.title ?? '';
  const tp = L.pop(L.start + Math.round(L.pulse * (matched ? 1 : 0.5)));
  const tSize = Math.min(layer.size ?? system.scale.hero,
    fitTextOnNLines({text: title || ' ', maxLines: 1, maxBoxWidth: (W - 300) / 1.12, fontFamily: `'${f.family}'`, fontWeight: f.weight,
      letterSpacing: `${f.tracking}em`, textTransform: f.case === 'none' ? undefined : f.case, maxFontSize: system.scale.hero * 1.4}).fontSize);
  const titleEl = title ? (
    <SafeBox name="parallax-title" justify={layer.titlePlace === 'bottom' ? 'end' : 'start'} align="center">
      <div
        style={{
          ...faceStyle(f),
          fontSize: tSize,
          color: color(layer.titleColor ?? 'paper'),
          whiteSpace: 'nowrap',
          transform: `translateY(${(1 - tp) * 60 + (layer.titlePlace === 'bottom' ? L.travel(0, -60) : L.travel(60, 0))}px) scale(${(0.92 + 0.08 * tp) * L.travel(1, 1.1)})`,
          transformOrigin: layer.titlePlace === 'bottom' ? '50% 100%' : '50% 0%',
          opacity: Math.min(1, tp),
        }}
      >
        {title}
      </div>
    </SafeBox>
  ) : null;
  if (layer.cutout) {
    return (
      <AbsoluteFill style={{overflow: 'hidden'}}>
        {back}
        {titleEl}
        <AbsoluteFill style={{transform: `scale(${L.travel(1.04, 1.26)}) translateY(${L.travel(1, -3)}%)`}}>
          <Img src={src(layer.cutout)} maxRetries={RETRIES} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: layer.pos ?? '50% 45%'}} />
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }
  const [wx, wy, ww, wh] = (layer.window as Box) ?? [0.14, 0.4, 0.72, 0.42];
  const wp = L.pop(L.start + Math.round(L.pulse * (matched ? 1.5 : 1)));
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      {back}
      {titleEl}
      <div
        style={{
          position: 'absolute',
          left: wx * W,
          top: wy * H,
          width: ww * W,
          height: wh * H,
          borderRadius: `${ww * W * 0.5}px ${ww * W * 0.5}px 8px 8px`,
          overflow: 'hidden',
          boxShadow: `0 40px 90px ${tint('#000000', 0.45)}`,
          transform: `translateY(${(1 - wp) * 40 + L.travel(14, -16)}%) scale(${(0.9 + 0.1 * wp) * L.travel(0.96, 1.06)})`,
          opacity: clamp01(wp * 1.5),
        }}
      >
        <AbsoluteFill style={{transform: `scale(${L.travel(1.45, 1.1)}) translateY(${L.travel(-8, 8)}%)`}}>
          <Photo file={file} pos={layer.pos} />
        </AbsoluteFill>
      </div>
    </AbsoluteFill>
  );
};

/**
 * Strip: a contact-sheet film strip of photos travelling across the frame, one frame per musical beat with a
 * constant creep between; a second row runs the other way.
 */
export const Strip: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system} = useSys();
  const color = useColor();
  const {W, H} = useSafe();
  const photos: string[] = layer.photos ?? [];
  const rows = Math.max(1, Math.min(2, layer.rows ?? 2));
  const bandH = (layer.height ?? 0.2) * H;
  const fw = bandH * 0.78 * 1.32;
  const pitch = fw + bandH * 0.08;
  const ink = color(layer.color ?? 'ink');
  const holes = color('paper');
  const enterP = L.tween(0, 1, L.start, Math.round(L.pulse * 1.2), 'enter');
  const step = (t: number) => {
    const k = Math.floor(t / L.pulse);
    const fr = (t - k * L.pulse) / L.pulse;
    return k + L.curves.move(Math.min(1, fr / 0.45));
  };
  const centers: number[] = layer.y ?? (rows === 2 ? [0.34, 0.6] : [0.45]);
  return (
    <AbsoluteFill style={{transform: `rotate(${layer.tilt ?? -5}deg) scale(1.12)`}}>
      {centers.slice(0, rows).map((cy, r) => {
        const dir = r % 2 === 0 ? -1 : 1;
        const travel = (step(L.local) + L.local / (L.pulse * 6)) * pitch;
        const off = dir * travel + (1 - enterP) * W * -dir * 1.1;
        const first = Math.floor((-off - pitch) / pitch) - 1;
        const count = Math.ceil(W / pitch) + 4;
        return (
          <div key={r} style={{position: 'absolute', left: -W * 0.1, width: W * 1.2, top: cy * H - bandH / 2, height: bandH, background: ink, overflow: 'hidden',
            boxShadow: `0 20px 50px ${tint('#000000', 0.4)}`}}>
            {Array.from({length: count}, (_, i) => {
              const idx = first + i;
              const x = idx * pitch + off;
              const photo = photos[((idx + r * 3) % photos.length + photos.length) % photos.length];
              return (
                <React.Fragment key={idx}>
                  <div style={{position: 'absolute', left: x, top: bandH * 0.11, width: fw, height: bandH * 0.78, overflow: 'hidden'}}>
                    <Photo file={photo} pos={layer.pos} />
                  </div>
                  {[0, 1, 2, 3].map((h) => (
                    <React.Fragment key={h}>
                      <div style={{position: 'absolute', left: x + (h * pitch) / 4 + 6, top: bandH * 0.025, width: pitch / 8, height: bandH * 0.05, borderRadius: 3, background: holes, opacity: 0.55}} />
                      <div style={{position: 'absolute', left: x + (h * pitch) / 4 + 6, bottom: bandH * 0.025, width: pitch / 8, height: bandH * 0.05, borderRadius: 3, background: holes, opacity: 0.55}} />
                    </React.Fragment>
                  ))}
                  <div style={{position: 'absolute', left: x + 4, top: bandH * 0.075, ...faceStyle(system.text), textTransform: 'none', letterSpacing: '0.04em',
                    fontSize: bandH * 0.035, lineHeight: 1, color: color('accent')}}>
                    {`${((idx % 36) + 36) % 36 + 1}${r ? 'A' : ''}`}
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/**
 * Polaroid: prints thrown onto the surface, one per beat, each spinning in from off frame and landing on the hit
 * spring with its shadow tightening as it drops; the stack grows and turns slowly.
 */
export const Polaroid: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system} = useSys();
  const color = useColor();
  const {W, H} = useSafe();
  const photos: string[] = layer.photos ?? [];
  const arr = L.arrivals(photos.length, layer.every ?? 1);
  const pw = (layer.width ?? 0.6) * W;
  const ph = pw * 1.18;
  const [cx, cy] = layer.center ?? [0.5, 0.42];
  const captions: string[] = layer.captions ?? [];
  const landed = arr.filter((a) => L.frame >= a).length;
  const gone = L.leave(Math.round(L.pulse * 0.8));
  return (
    <AbsoluteFill style={{transformOrigin: `${cx * 100}% ${cy * 100}%`, transform: `rotate(${L.travel(-3, 3)}deg) translate(${L.travel(-3, 3)}%, ${L.travel(2, -2) + gone * 120}%) scale(${L.travel(1, 1.06)})`}}>
      {arr.map((a, k) => {
        if (L.frame < a - 1 || k < landed - 4) return null;
        const p = L.hit(a);
        const s = L.pop(a, {damping: 30, stiffness: 140});
        const side = k % 2 === 0 ? -1 : 1;
        const endRot = (hash(`pr${k}${photos[k]}`) - 0.5) * 16;
        const ex = (hash(`px${k}`) - 0.5) * 0.14 * W;
        const ey = (hash(`py${k}`) - 0.5) * 0.08 * H;
        const x = cx * W - pw / 2 + ex + (1 - s) * side * W * 0.75;
        const y = cy * H - ph / 2 + ey + (1 - s) * H * 0.5;
        const rot = endRot + (1 - p) * side * 35;
        const lift = 1 - s;
        return (
          <div
            key={k}
            style={{
              position: 'absolute',
              left: x,
              top: y,
              width: pw,
              height: ph,
              background: color('paper'),
              padding: `${pw * 0.05}px ${pw * 0.05}px ${pw * 0.2}px`,
              boxSizing: 'border-box',
              transform: `rotate(${rot}deg) scale(${1 + 0.25 * lift})`,
              boxShadow: `${10 + 40 * lift}px ${20 + 70 * lift}px ${30 + 90 * lift}px ${tint('#000000', 0.35 + 0.15 * (1 - lift))}`,
              filter: landed - 1 - k > 0 ? `brightness(${1 - 0.07 * (landed - 1 - k)})` : undefined,
            }}
          >
            <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden', background: system.colors.ink}}>
              <LivePhoto file={photos[k]} pos={layer.pos} from={1.06} to={1.12} dx={1} dy={-1} />
            </div>
            {captions[k] ? (
              <div style={{position: 'absolute', left: pw * 0.06, right: pw * 0.06, bottom: pw * 0.05, height: pw * 0.11, display: 'flex', alignItems: 'center',
                ...faceStyle(system.text), textTransform: 'none', letterSpacing: '0.02em', fontSize: pw * 0.055, color: system.colors.ink, whiteSpace: 'nowrap', overflow: 'hidden'}}>
                {captions[k]}
              </div>
            ) : null}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

/** Push: the push-and-drift, a breath between loud beats, never longer than one bar. */
export const Push: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const file: string = layer.photo ?? pick(layer.photos, 0);
  const dir = hash(file) > 0.5 ? 1 : -1;
  return (
    <AbsoluteFill style={{overflow: 'hidden'}}>
      <AbsoluteFill style={{transform: `scale(${L.travel(layer.from ?? 1.0, layer.to ?? 1.14)}) translate(${L.travel(-2 * dir, 2 * dir)}%, ${L.travel(1.5, -1.5)}%) rotate(${L.travel(-0.6 * dir, 0.6 * dir)}deg)`}}>
        <Photo file={file} pos={layer.pos} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** The clip's frame sequence (conformed by clips.py), looping past its end; a still brought to life when it has none. */
const ClipFrames: React.FC<{clip: Clip | null | undefined; image?: string; from: number}> = ({clip, image, from}) => {
  const {frame, travel} = useMotion();
  const {system} = useSys();
  if (clip?.file && clip.frames) {
    const i = (((Math.max(0, frame - from) % clip.frames) + clip.frames) % clip.frames) + 1;
    return (
      <AbsoluteFill style={{transform: `scale(${travel(1.08, 1.22)}) translate(${travel(-3, 3)}%, ${travel(2, -2)}%)`}}>
        <Img src={src(`${clip.file.replace(/\.mp4$/, '')}/${String(i).padStart(4, '0')}.jpg`)} maxRetries={RETRIES}
          style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: `50% ${travel(30, 70)}%`}} />
      </AbsoluteFill>
    );
  }
  const file = clip?.image ?? image ?? '';
  const dust = Array.from({length: 22}, (_, k) => {
    const x = random(`dx${k}`) * 100;
    const y = (random(`dy${k}`) * 100 - frame * (0.03 + random(`ds${k}`) * 0.05) + 200) % 100;
    const s = 2 + random(`dz${k}`) * 5;
    return <div key={k} style={{position: 'absolute', left: `${x}%`, top: `${y}%`, width: s, height: s, borderRadius: s, background: system.colors.paper, opacity: 0.4}} />;
  });
  return (
    <AbsoluteFill>
      <LivePhoto file={file} from={1.06} to={1.2} dx={2} dy={-2} />
      <AbsoluteFill>{dust}</AbsoluteFill>
    </AbsoluteFill>
  );
};

/**
 * ClipShot: a clip inside a frame, never raw over the whole frame.
 * inset   a framed window that wipes up into place with a running timecode
 * circle  a circular window opening on the hit spring, a dashed ring turning around it
 * band    a horizontal band across the frame opening from its centre line
 */
export const ClipShot: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system} = useSys();
  const color = useColor();
  const {W, H} = useSafe();
  const clip = layer.clip as Clip | null | undefined;
  const frame: string = layer.frame ?? 'inset';
  const body = <ClipFrames clip={clip} image={layer.photo} from={L.start} />;
  if (frame === 'circle') {
    const p = L.hit(L.start);
    const [ox, oy] = layer.origin ?? [0.5, 0.4];
    const r = (layer.radius ?? 0.42) * W * p + L.travel(0, 0.03) * W;
    return (
      <AbsoluteFill>
        <AbsoluteFill style={{clipPath: `circle(${Math.max(0, r)}px at ${ox * 100}% ${oy * 100}%)`}}>{body}</AbsoluteFill>
        <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
          <circle cx={ox * W} cy={oy * H} r={r + 22} fill="none" stroke={color(layer.color ?? 'accent')} strokeWidth={6} strokeDasharray="30 16"
            transform={`rotate(${L.travel(0, -90)} ${ox * W} ${oy * H})`} opacity={clamp01(p)} />
        </svg>
      </AbsoluteFill>
    );
  }
  if (frame === 'band') {
    const p = L.tween(0, 1, L.start, Math.round(L.pulse), 'enter');
    const [cy, bh] = [layer.y ?? 0.42, layer.height ?? 0.34];
    return (
      <AbsoluteFill>
        <div style={{position: 'absolute', left: 0, width: W, top: (cy - bh / 2) * H, height: bh * H, overflow: 'hidden', clipPath: `inset(${(1 - p) * 50}% 0)`}}>
          {body}
        </div>
        {[-1, 1].map((s) => (
          <div key={s} style={{position: 'absolute', left: 0, width: W, height: 5, top: (cy + (s * bh) / 2) * H + (s < 0 ? -12 : 7) + s * (1 - p) * -bh * H * 0.5,
            background: color(layer.color ?? 'accent'), transformOrigin: s < 0 ? '0% 50%' : '100% 50%', transform: `scaleX(${p})`}} />
        ))}
      </AbsoluteFill>
    );
  }
  const b = useBox(layer.box, [0.08, 0.15, 0.84, 0.5]);
  const p = L.pop(L.start);
  const secs = Math.max(0, L.frame - L.start) / L.fps;
  const tc = `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(Math.floor(secs % 60)).padStart(2, '0')}:${String(Math.floor((secs * L.fps) % L.fps)).padStart(2, '0')}`;
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: b.left, top: b.top, width: b.width, height: b.height, transform: `translateY(${(1 - p) * 30 + L.travel(1, -2)}%)`,
        clipPath: `inset(${(1 - p) * 100}% 0 0 0)`, background: color('paper'), padding: 5, boxSizing: 'border-box', boxShadow: `0 40px 90px ${tint('#000000', 0.45)}`}}>
        <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden'}}>
          {body}
          <div style={{position: 'absolute', left: 22, top: 18, display: 'flex', alignItems: 'center', gap: 10, ...faceStyle(system.text), textTransform: 'none',
            letterSpacing: '0.06em', fontSize: 26, color: '#ffffff', textShadow: '0 2px 8px rgba(0,0,0,0.6)'}}>
            <div style={{width: 14, height: 14, borderRadius: 7, background: '#ff3b30', opacity: Math.floor(L.frame / 15) % 2 ? 0.35 : 1}} />
            {tc}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

type Crop = [number, number, number];

/**
 * Picture: one photograph placed by the composition: `box` [x, y, w, h] in fractions of the frame (absent: full
 * bleed), `crop` [x, y, w] in fractions of the source (absent: the cover crop), turned by `rotate` degrees. It never
 * drifts inside its box, so its `marks` (marks.tsx) stay on the points of the picture they were drawn on, and the
 * beat's camera moves picture and marks together. `print` gives it a paper border of that many px and a cast
 * shadow; `filter` is a CSS filter on the photograph; `dim` darkens it toward the palette's dark by that share,
 * evenly, or with `dimTo` as a gradient toward that side that starts at `dimFrom` and reaches the share at `dimEnd`
 * (fractions of the box), past which it goes fully dark.
 * `enter` is how it arrives: cut (there from its `at`), fade, or drop (a print landing on the hit spring); at `out`
 * a cut leaves on that frame and a fade or a drop fades away. `pan` [dx, dy] (fractions of the source) starts the
 * crop that far off and travels it, at an even speed, onto `crop` by `panTo` musical beats after the entrance
 * (absent: its exit, else the beat's end); its marks travel with it, so the composition settles as designed.
 * Without a `file` it is marks alone, laid over the frame in the frame's own fractions (`aspect` 1.778).
 */
export const Picture: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system} = useSys();
  const {W, H} = useSafe();
  const [bx, by, bw, bh] = (layer.box as Box | undefined) ?? [0, 0, 1, 1];
  const w = bw * W;
  const h = bh * H;
  const border: number = layer.print ?? 0;
  const enter: string = layer.enter ?? 'cut';
  const p = enter === 'drop' ? L.hit(L.start) : 1;
  const fade = enter === 'fade' ? L.tween(0, 1, L.start, Math.round(L.pulse), 'enter') : 1;
  const shown = enter === 'cut' && L.frame < L.start ? 0 : 1;
  const out = enter === 'cut' ? (L.end !== null && L.frame >= L.end ? 0 : 1) : 1 - L.leave();
  const rot = (layer.rotate ?? 0) + (1 - p) * 6;
  const sc = 1 + (1 - p) * 0.12;
  const shadow = layer.shadow ?? (border ? 0.45 : 0);
  const c0 = layer.crop as Crop | undefined;
  const pan = layer.pan as [number, number] | undefined;
  const panEnd = layer.panTo !== undefined ? L.start + L.at(layer.panTo) : L.end ?? L.duration;
  const left = pan && c0 ? Math.max(0, Math.min(1, 1 - (L.frame - L.start) / Math.max(1, panEnd - L.start))) : 0;
  const crop: Crop | undefined = c0 && pan ? [c0[0] + pan[0] * left, c0[1] + pan[1] * left, c0[2]] : c0;
  return (
    <div style={{position: 'absolute', left: bx * W, top: by * H, width: w, height: h, opacity: shown * fade * out * Math.min(1, p * 3),
      transform: `rotate(${rot}deg) scale(${sc})`, transformOrigin: '50% 50%'}}>
      {border || shadow ? (
        <div style={{position: 'absolute', inset: -border, background: layer.paper ? system.colors[layer.paper as 'paper'] ?? layer.paper : system.colors.paper,
          boxShadow: shadow ? `0 ${34 * shadow * p}px ${90 * shadow}px ${tint('#000000', shadow)}, 0 ${5 * shadow}px ${12 * shadow}px ${tint('#000000', shadow * 0.7)}` : undefined}} />
      ) : null}
      {layer.file ? <PhotoIn file={layer.file} aspect={layer.aspect ?? 0.667} w={w} h={h} crop={crop} filter={layer.filter} /> : null}
      {layer.dim ? <div style={{position: 'absolute', inset: 0, background: layer.dimTo
        ? `linear-gradient(to ${layer.dimTo}, ${tint(system.colors.bg, 0)} ${(layer.dimFrom ?? 0) * 100}%, ${tint(system.colors.bg, layer.dim)} ${(layer.dimEnd ?? 1) * 100}%${layer.dimEnd ? `, ${tint(system.colors.bg, 1)} 100%` : ''})` : tint(system.colors.bg, layer.dim)}} /> : null}
      {layer.marks ? <Marks marks={layer.marks as Mark[]} aspect={layer.aspect ?? 0.667} w={w} h={h} crop={crop} start={L.start}
        id={String(layer.id)} origin={[bx * W, by * H]} /> : null}
    </div>
  );
};

type SheetFrame = {file: string; aspect: number; crop?: Crop; filter?: string; marks?: Mark[]; n?: string};

/**
 * Sheet: a contact sheet: the year's negatives laid in strips on the paper, `cols` frames to a strip, each strip on
 * its black rebate with sprocket holes and edge numbers. Every frame is a 3:2 window on its source: `crop` [x, y, w]
 * picks the framing and `filter` the exposure, so a roll's neighbours differ by framing, exposure and a step of the subject.
 * Each frame's `marks` are drawn in that frame's coordinates over the whole sheet, the way a grease pencil crosses
 * the strips. `box` [x, y, w] places the sheet; `rotate` turns it on the table.
 */
export const Sheet: React.FC<P> = ({layer}) => {
  const L = useLayer(layer);
  const {system} = useSys();
  const {W, H} = useSafe();
  const [bx, by, bw] = (layer.box as [number, number, number] | undefined) ?? [0.04, 0.2, 0.92];
  const cols: number = layer.cols ?? 4;
  const frames: SheetFrame[] = layer.frames ?? [];
  const sw = bw * W;
  const gap = sw * 0.012;
  const fw = (sw - gap * (cols + 1)) / cols;
  const fh = fw * (2 / 3);
  const reb = fh * 0.2;
  const stripH = fh + reb * 2;
  const rows = Math.ceil(frames.length / cols);
  const rowGap = reb * 0.9;
  const edge: string = layer.edge ?? '';
  const ink = '#e9e1d2';
  const cell = (k: number) => {
    const r = Math.floor(k / cols);
    const c = k % cols;
    return {x: gap + c * (fw + gap), y: r * (stripH + rowGap) + reb, r};
  };
  const shown = L.frame < L.start ? 0 : 1;
  const holes = Math.round(sw / (fh * 0.16));
  return (
    <div style={{position: 'absolute', left: bx * W, top: by * H, width: sw, height: rows * (stripH + rowGap), opacity: shown,
      transform: `rotate(${layer.rotate ?? 0}deg)`, transformOrigin: '50% 40%'}}>
      {Array.from({length: rows}, (_, r) => {
        const jx = (hash(`${layer.id}-x${r}`) - 0.5) * sw * 0.02;
        const jr = (hash(`${layer.id}-r${r}`) - 0.5) * 0.7;
        return (
          <div key={r} style={{position: 'absolute', left: jx, top: r * (stripH + rowGap), width: sw, height: stripH, background: layer.rebate ?? '#121010',
            transform: `rotate(${jr}deg)`, boxShadow: `0 6px 18px ${tint('#000000', 0.25)}`}}>
            {[0, 1].map((side) => (
              <div key={side} style={{position: 'absolute', left: 0, right: 0, top: side ? stripH - reb * 0.62 : reb * 0.22, height: reb * 0.4, display: 'flex',
                justifyContent: 'space-around'}}>
                {Array.from({length: holes}, (_, j) => <div key={j} style={{width: fh * 0.07, height: '100%', borderRadius: 3, background: system.colors.paper, opacity: 0.85}} />)}
              </div>
            ))}
            {frames.slice(r * cols, r * cols + cols).map((fr, c) => {
              const k = r * cols + c;
              const {x} = cell(k);
              return (
                <React.Fragment key={c}>
                  <div style={{position: 'absolute', left: x, top: reb, width: fw, height: fh, overflow: 'hidden', background: '#000'}}>
                    <PhotoIn file={fr.file} aspect={fr.aspect} w={fw} h={fh} crop={fr.crop} filter={fr.filter} />
                  </div>
                  <div style={{position: 'absolute', left: x + 4, top: stripH - reb * 0.2 - 2, fontFamily: `'${system.text.family}'`, fontSize: reb * 0.17,
                    fontWeight: 600, letterSpacing: '0.12em', color: ink, opacity: 0.8, whiteSpace: 'nowrap', lineHeight: 1}}>
                    {fr.n ?? String(k + 1)} {c === 0 && edge ? `   ${edge}` : ''}
                  </div>
                </React.Fragment>
              );
            })}
          </div>
        );
      })}
      {frames.map((fr, k) => {
        if (!fr.marks) return null;
        const {x, y} = cell(k);
        return (
          <div key={`m${k}`} style={{position: 'absolute', left: x, top: y, width: fw, height: fh}}>
            <Marks marks={fr.marks} aspect={fr.aspect} w={fw} h={fh} crop={fr.crop} start={L.start} id={`${layer.id}-${k}`}
              origin={[bx * W + x, by * H + y]} />
          </div>
        );
      })}
    </div>
  );
};
