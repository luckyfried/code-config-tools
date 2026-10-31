// tape-slap: the picture laid on the page inside a margin of the card's ground, two strips of the card's tape slapped
// across its corners one after the other and settling flat.
import React from 'react';
import {alpha, fill, hash, land, px, Window} from '../kit';
import type {Move, MoveProps} from '../types';

const Tape: React.FC<{x: number; y: number; deg: number; k: number; w: number; color: string; shade: string}> = ({x, y, deg, k, w, color, shade}) => (
  <div style={{position: 'absolute', left: x - w / 2, top: y - w * 0.14, width: w, height: w * 0.28, background: color, opacity: 0.82 * Math.min(1, 0.3 + k * 3),
    transform: `rotate(${deg}deg) scale(${1.5 - 0.5 * k})`, boxShadow: `0 2px 6px ${alpha(shade, 0.18)}`}} />
);

const Overlay: React.FC<MoveProps> = ({look, local, seed}) => {
  const m = px(look, 90);
  const top = look.H * 0.16, h = look.H * 0.62;
  const w = px(look, 300);
  return (
    <div style={fill}>
      <Window box={[m, top, look.W - 2 * m, h]} color={look.tone.ground} rotate={(look.print.tilt || -1.5) * 0.5 * (0.5 + hash(seed))} />
      <Tape x={m + px(look, 20)} y={top + px(look, 10)} deg={-38} k={land(0.1 + local * 1.6)} w={w} color={look.tone.tape} shade={look.tone.matte} />
      <Tape x={look.W - m - px(look, 20)} y={top + h - px(look, 10)} deg={-36} k={land(Math.max(0, local - 0.5) * 1.6)} w={w} color={look.tone.tape} shade={look.tone.matte} />
    </div>
  );
};

export default {Overlay} satisfies Move;
