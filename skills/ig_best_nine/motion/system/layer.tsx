import React from 'react';
import {AbsoluteFill, Img} from 'remotion';
import {src, tint, useMotion, useSafe, useSys} from './system';
import type {Layer} from './types';

/** Image requests retry with backoff (1 s, 2 s, 4 s ...), so a dropped request costs a pause, never the render. */
export const RETRIES = 6;

/** A layer's clock: where it enters and leaves in frames of the beat, and its springs and tweens from there. */
export const useLayer = (l: Layer) => {
  const m = useMotion();
  const start = m.at(l.at);
  const end = m.still || l.out === undefined || l.out === null ? null : m.at(l.out);
  /** frames of each arrival: the layer's entrance, then one every `every` musical beats */
  const arrivals = (n: number, every = 1) => Array.from({length: n}, (_, k) => start + Math.round(k * every * m.pulse));
  /** 0 until the layer starts leaving, then 1 over `dur` frames */
  const leave = (dur = Math.round(m.pulse * 0.75), lead = 0) => (end === null ? 0 : m.tween(0, 1, end + lead, dur, 'exit'));
  /** frames since the layer entered, never below 0 */
  const local = Math.max(0, m.frame - start);
  return {...m, start, end, arrivals, leave, local};
};

/** A box in fractions of the frame: [x, y, w, h]. */
export type Box = [number, number, number, number];

export const useBox = (box: Box | undefined, fallback: Box) => {
  const {W, H} = useSafe();
  const [x, y, w, h] = box ?? fallback;
  return {left: x * W, top: y * H, width: w * W, height: h * H, W, H};
};

/** The photograph, filling its box. `pos` is its focal point (object-position). */
export const Photo: React.FC<{file: string; pos?: string; style?: React.CSSProperties}> = ({file, pos, style}) => (
  <Img
    src={src(file)}
    maxRetries={RETRIES}
    style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: pos ?? '50% 45%', display: 'block', ...style}}
  />
);

/** A photograph alive inside its frame: an eased push and a drift across the beat, never standing still. */
export const LivePhoto: React.FC<{file: string; pos?: string; from?: number; to?: number; dx?: number; dy?: number; style?: React.CSSProperties}> = ({
  file,
  pos,
  from = 1.08,
  to = 1.18,
  dx = 2,
  dy = -1.5,
  style,
}) => {
  const {travel} = useMotion();
  return (
    <AbsoluteFill style={{overflow: 'hidden', ...style}}>
      <AbsoluteFill style={{transform: `scale(${travel(from, to)}) translate(${travel(-dx, dx)}%, ${travel(-dy, dy)}%)`}}>
        <Photo file={file} pos={pos} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** A print: the photo with a thin paper frame and a cast shadow. */
export const Print: React.FC<{file: string; border?: number; shadow?: number; pos?: string; live?: boolean; color?: string; children?: React.ReactNode}> = ({
  file,
  border = 3,
  shadow = 0.45,
  pos,
  live = true,
  color,
  children,
}) => {
  const {system} = useSys();
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: color ?? system.colors.paper,
        padding: border,
        boxShadow: `0 ${30 * shadow}px ${80 * shadow}px ${tint('#000000', shadow)}, 0 ${6 * shadow}px ${14 * shadow}px ${tint('#000000', shadow * 0.6)}`,
      }}
    >
      <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden'}}>
        {live ? <LivePhoto file={file} pos={pos} from={1.04} to={1.12} dx={1.5} dy={-1} /> : <Photo file={file} pos={pos} />}
        {children}
      </div>
    </div>
  );
};

/** One photo per arrival, cycling through the list when there are more arrivals than photos. */
export const pick = (photos: string[] | undefined, k: number) => (photos && photos.length ? photos[k % photos.length] : '');
