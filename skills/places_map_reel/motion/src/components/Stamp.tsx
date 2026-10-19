import React from 'react';
import {AbsoluteFill, Img, useVideoConfig} from 'remotion';
import {faceStyle, hash, src, useMotion, useSafe, useSys} from '../system';
import {Headline, Kicker, Line, SafeBox} from '../text';
import {RETRIES} from '../photo';
import type {Beat, StampData} from '../types';

const alpha = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
};

const ASPECT = {circle: 1, rect: 0.82, octagon: 1, oval: 0.76} as const;

const outline = (shape: StampData['shape'], w: number, h: number, inset: number) => {
  const x = inset;
  const y = inset;
  const ww = w - 2 * inset;
  const hh = h - 2 * inset;
  if (shape === 'circle' || shape === 'oval') return <ellipse cx={w / 2} cy={h / 2} rx={ww / 2} ry={hh / 2} />;
  if (shape === 'rect') return <rect x={x} y={y} width={ww} height={hh} rx={Math.min(ww, hh) * 0.06} />;
  const c = Math.min(ww, hh) * 0.29;
  const pts = [[x + c, y], [x + ww - c, y], [x + ww, y + c], [x + ww, y + hh - c], [x + ww - c, y + hh], [x + c, y + hh], [x, y + hh - c], [x, y + c]];
  return <polygon points={pts.map((p) => p.join(',')).join(' ')} />;
};

const clipFor = (shape: StampData['shape'], inset: number) => {
  if (shape === 'circle' || shape === 'oval') return `ellipse(${50 - inset}% ${50 - inset}% at 50% 50%)`;
  if (shape === 'rect') return `inset(${inset}% round 4%)`;
  const a = inset;
  const c = 29 * (1 - (2 * inset) / 100) + inset;
  return `polygon(${c}% ${a}%, ${100 - c}% ${a}%, ${100 - a}% ${c}%, ${100 - a}% ${100 - c}%, ${100 - c}% ${100 - a}%, ${c}% ${100 - a}%, ${a}% ${100 - c}%, ${a}% ${c}%)`;
};

/** The photos inside a stamp: one fills it, two share it, three set one large beside two small. */
const Mosaic: React.FC<{photos: string[]; drift: number}> = ({photos, drift}) => {
  const img = (f: string, style: React.CSSProperties) => (
    <div style={{position: 'absolute', overflow: 'hidden', ...style}}>
      <Img src={src(f)} maxRetries={RETRIES} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${drift})`}} />
    </div>
  );
  if (photos.length >= 3) {
    return (
      <>
        {img(photos[0], {left: 0, top: 0, width: '58%', height: '100%'})}
        {img(photos[1], {left: '59%', top: 0, width: '41%', height: '49.5%'})}
        {img(photos[2], {left: '59%', top: '50.5%', width: '41%', height: '49.5%'})}
      </>
    );
  }
  if (photos.length === 2) {
    return (
      <>
        {img(photos[0], {left: 0, top: 0, width: '49.6%', height: '100%'})}
        {img(photos[1], {left: '50.4%', top: 0, width: '49.6%', height: '100%'})}
      </>
    );
  }
  return photos[0] ? img(photos[0], {left: 0, top: 0, width: '100%', height: '100%'}) : null;
};

/** One place's stamp: an inked border in its shape, its photos inside, its name on a band and its dates. */
export const StampMark: React.FC<{stamp: StampData; size: number; ink: string; paper: string; drift?: number; detail?: boolean}> = ({
  stamp,
  size,
  ink,
  paper,
  drift = 1.06,
  detail = true,
}) => {
  const {system} = useSys();
  const w = size;
  const h = Math.round(size * ASPECT[stamp.shape]);
  const id = `rough-${stamp.id}-${size}`;
  const band = Math.round(h * 0.15);
  return (
    <div style={{position: 'relative', width: w, height: h}}>
      <div style={{position: 'absolute', inset: 0, clipPath: clipFor(stamp.shape, 9), background: paper}}>
        <div style={{position: 'absolute', inset: 0, filter: 'sepia(0.18) saturate(0.92) contrast(1.04)'}}>
          <Mosaic photos={stamp.photos} drift={drift} />
        </div>
        <div style={{position: 'absolute', inset: 0, background: ink, mixBlendMode: 'multiply', opacity: 0.16}} />
      </div>
      <svg width={w} height={h} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
        <defs>
          <filter id={id}>
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={Math.round(hash(stamp.id) * 100)} />
            <feDisplacementMap in="SourceGraphic" scale={Math.max(2, size / 140)} />
          </filter>
        </defs>
        <g fill="none" stroke={ink} filter={`url(#${id})`}>
          <g strokeWidth={Math.max(3, size * 0.022)}>{outline(stamp.shape, w, h, size * 0.02)}</g>
          <g strokeWidth={Math.max(1.5, size * 0.008)}>{outline(stamp.shape, w, h, size * 0.06)}</g>
        </g>
      </svg>
      {detail ? (
        <div
          style={{
            position: 'absolute',
            left: '12%',
            right: '12%',
            top: Math.round(h * 0.68),
            height: band,
            background: ink,
            color: paper,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            ...faceStyle(system.display),
            fontSize: Math.round(band * 0.62),
            lineHeight: 1,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            transform: 'rotate(-2deg)',
          }}
        >
          {stamp.name}
        </div>
      ) : null}
    </div>
  );
};

const inkOf = (i: number, c: {accent: string; accent2: string; ink: string}) => [c.accent, c.ink, c.accent2][i % 3];

/** Where the earlier stamps sit on the page: a loose grid with a little jitter, the same every frame. */
const scatter = (i: number, W: number, H: number, s: {top: number}) => {
  const cols = 3;
  const cw = W / cols;
  const ch = 330;
  const col = i % cols;
  const row = Math.floor(i / cols) % 4;
  return {
    x: col * cw + cw / 2 + (hash(`x${i}`) - 0.5) * 70,
    y: s.top - 120 + row * ch + ch / 2 + (hash(`y${i}`) - 0.5) * 60,
  };
};

/**
 * The passport. stamp: the page with the earlier stamps on it, and the new place's stamp coming down onto it
 * with a thump. page: every stamp of the year laid out on one page.
 */
export const Stamp: React.FC<{beat: Beat}> = ({beat}) => {
  const {system} = useSys();
  const {width: W, height: H} = useVideoConfig();
  const s = useSafe();
  const {frame, tween, pop, drift, duration} = useMotion();
  const d = beat.data ?? {};
  const c = system.colors;
  const paper = c.paper;
  const page: StampData[] = d.page ?? [];
  const t = beat.text ?? {};
  const lines = Array.from({length: 26}, (_, i) => {
    const y = 40 + i * 74;
    const a = 10 + (i % 3) * 4;
    return `M0 ${y} C ${W * 0.25} ${y - a}, ${W * 0.5} ${y + a}, ${W * 0.75} ${y - a} S ${W} ${y + a}, ${W + 40} ${y}`;
  });
  const guilloche = (
    <svg width={W} height={H} style={{position: 'absolute', left: 0, top: 0}}>
      {lines.map((p, i) => (
        <path key={i} d={p} fill="none" stroke={alpha(c.muted, 0.16)} strokeWidth={1.4} />
      ))}
    </svg>
  );
  if (d.mode === 'page') {
    const n = page.length;
    const cols = n <= 4 ? 2 : n <= 9 ? 3 : 4;
    const rows = Math.ceil(n / cols);
    const top = 150;
    const bottom = H - s.bottom - 420;
    const cell = Math.min((W - 80) / cols, (bottom - top) / rows);
    return (
      <AbsoluteFill style={{background: paper}}>
        {guilloche}
        {page.map((st, i) => {
          const p = pop(4 + i * 3);
          const col = i % cols;
          const row = Math.floor(i / cols);
          const left = (W - cols * cell) / 2 + col * cell + (cell - cell * 0.86) / 2;
          const y = top + row * cell + (cell - cell * 0.86 * (st.shape === 'oval' ? 0.76 : st.shape === 'rect' ? 0.82 : 1)) / 2;
          return (
            <div key={st.id} style={{position: 'absolute', left, top: y, transform: `rotate(${st.tilt}deg) scale(${1.5 - 0.5 * p})`, opacity: Math.min(1, p * 1.8)}}>
              <StampMark stamp={st} size={Math.round(cell * 0.86)} ink={inkOf(i, c)} paper={paper} />
            </div>
          );
        })}
        <SafeBox name="page" justify="end">
          {t.kicker ? <Kicker text={t.kicker} delay={6 + n * 3} /> : null}
          {t.headline ? <Headline text={t.headline} max="h1" lines={2} delay={10 + n * 3} /> : null}
          {t.line ? <Line text={t.line} delay={18 + n * 3} /> : null}
        </SafeBox>
      </AbsoluteFill>
    );
  }
  const st: StampData = d.stamp;
  const hit = 9;
  const p = pop(2, {damping: 16, stiffness: 170});
  const shake = frame >= hit && frame < hit + 8 ? Math.sin((frame - hit) * 2.4) * (8 - (frame - hit)) * 1.2 : 0;
  const size = 640;
  const sh = Math.round(size * ASPECT[st.shape]);
  const cx = (W - size) / 2;
  const cy = s.top + Math.max(0, (H - s.top - s.bottom - 290 - sh) / 2);
  const ring = tween(0, 1, hit, 18);
  return (
    <AbsoluteFill style={{background: paper, transform: `translate(${shake}px, ${shake * 0.6}px)`}}>
      {guilloche}
      {page.map((q, i) => {
        const at = scatter(i, W, H, s);
        return (
          <div key={q.id} style={{position: 'absolute', left: at.x - 130, top: at.y - 130, transform: `rotate(${q.tilt}deg)`, opacity: 0.55}}>
            <StampMark stamp={q} size={260} ink={inkOf(i, c)} paper={paper} detail />
          </div>
        );
      })}
      <div style={{position: 'absolute', left: cx - 40, top: cy - 40, width: size + 80, height: sh + 80, borderRadius: '50%',
        border: `6px solid ${alpha(inkOf(page.length, c), 0.35 * (1 - ring))}`, transform: `scale(${0.9 + ring * 0.4})`, opacity: ring > 0 ? 1 : 0}} />
      <div
        style={{
          position: 'absolute',
          left: cx,
          top: cy,
          transform: `rotate(${st.tilt + (1 - p) * -10}deg) scale(${1.7 - 0.7 * p})`,
          opacity: Math.min(1, p * 2.2),
          filter: `drop-shadow(0 ${30 * (1 - p)}px ${40 * (1 - p)}px rgba(0,0,0,0.35))`,
        }}
      >
        <StampMark stamp={st} size={size} ink={inkOf(page.length, c)} paper={paper} drift={drift(1.04, 1.14)} />
      </div>
      <SafeBox name="stamp" justify="end">
        {t.kicker ? <Kicker text={t.kicker} delay={hit} /> : null}
        {t.headline ? <Headline text={t.headline} max="h1" lines={1} delay={hit + 3} /> : null}
        {t.line ? <Line text={t.line} delay={hit + 12} /> : null}
      </SafeBox>
    </AbsoluteFill>
  );
};
