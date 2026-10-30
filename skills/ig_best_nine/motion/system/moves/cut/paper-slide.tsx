// paper-slide: a torn strip of the card's ground slides up across the frame on a tilt while the camera travels to the
// next beat; the strip covers a band of the frame, never the whole of it. Both long edges are torn: a slow wander, a
// finer ragged run and a fibre's jitter, traced every two frame pixels so the tear holds at full size, with the paper's
// pale core showing a hair past the ground along it, as torn paper does.
import React from 'react';
import {alpha, fill, hash, px, SINE, smoothNoise} from '../kit';
import type {Cut, CutProps} from '../types';

/** How far in from the strip's straight edge the tear runs at `x` px along it, 0 to `depth`, for one edge's `seed`. */
const torn = (x: number, seed: number, wander: number, ragged: number, depth: number) =>
  depth * (0.55 * (smoothNoise(x / wander, seed) + 1) / 2 + 0.3 * (smoothNoise(x / ragged, seed + 3) + 1) / 2 + 0.15 * (hash(x * 0.731 + seed * 19.7) + 1) / 2);

const Overlay: React.FC<CutProps> = ({look, u}) => {
  const h = look.H * 0.42;
  const y = look.H * 1.05 - SINE(u) * (look.H * 1.1 + h);
  const over = px(look, 40), w = look.W + 2 * over;
  const depth = px(look, 22), wander = px(look, 90), ragged = px(look, 22), core = px(look, 3);
  const xs = Array.from({length: Math.ceil(w / 2) + 1}, (_, i) => Math.min(w, i * 2));
  const edge = (inset: number, lift: number) => {
    const top = xs.map((x) => `${x.toFixed(1)},${(torn(x, 1, wander, ragged, depth) - inset - lift * (hash(x * 1.37 + 5) + 1)).toFixed(1)}`);
    const foot = xs.map((x) => `${x.toFixed(1)},${(h - torn(x, 2, wander, ragged, depth) + inset + lift * (hash(x * 1.91 + 9) + 1)).toFixed(1)}`).reverse();
    return [...top, ...foot].join(' ');
  };
  return (
    <div style={fill}>
      <svg width={w} height={h + 2 * depth} viewBox={`0 ${-depth} ${w} ${h + 2 * depth}`}
        style={{position: 'absolute', left: -over, top: y - depth, overflow: 'visible', transform: 'rotate(-4deg)',
          filter: `drop-shadow(0 ${px(look, 14)}px ${px(look, 24)}px ${alpha(look.tone.matte, 0.3)})`}}>
        <polygon points={edge(core * 0.5, core * 0.5)} fill={look.tone.rim} />
        <polygon points={edge(0, 0)} fill={look.tone.ground} />
      </svg>
    </div>
  );
};

export default {beats: 1.2, jump: false, Overlay} satisfies Cut;
