// sticker-pop: a round sticker of the card's accent with a rim of the card's paper pops onto the print's top corner with
// an overshoot, the beat's label printed on it, or a drawn star when the card sets the beat's words itself; the page
// drifts a little under it while the beat holds.
import React from 'react';
import {alpha, fill, fit, follow, hash, heldOf, land, pictureOf, px, Words} from '../kit';
import type {Move, MoveProps} from '../types';

const nudge = ({u}: {u: number}) => ({dx: 0.012 * (u - 0.5), dy: -0.006 * u, roll: 0.006 * (u - 0.5)});

const Star: React.FC<{d: number; color: string}> = ({d, color}) => {
  const pts = Array.from({length: 10}, (_, i) => {
    const r = (i % 2 ? 0.2 : 0.42) * d, a = -Math.PI / 2 + (i * Math.PI) / 5;
    return `${d / 2 + r * Math.cos(a)},${d / 2 + r * Math.sin(a)}`;
  }).join(' ');
  return <svg width={d} height={d}><polygon points={pts} fill="none" stroke={color} strokeWidth={d * 0.05} strokeLinejoin="round" /></svg>;
};

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, local, seed, t} = p;
  const text = beat.label || beat.words.split(/\s+/).slice(0, 2).join(' ');
  const k = land(Math.max(0, local - 0.15) * 1.2);
  const [bx, by, bw] = beat.box ? pictureOf(look, beat) : [look.W * 0.2, look.H * 0.2, look.W * 0.6, look.H * 0.3];
  const d = Math.min(px(look, 300), bw * 0.36);
  // the sticker's middle on the print's top right corner, clear of the words under the print
  const right = hash(seed) > 0.5;
  const edge = px(look, 40) + d / 2;
  const cx = Math.min(look.W - edge, Math.max(edge, right ? bx + bw - d * 0.18 : bx + d * 0.18)), cy = Math.max(edge, by + d * 0.12);
  return (
    <div style={{...fill, opacity: heldOf(beat, t), ...(beat.box ? follow(look, nudge(p)) : {})}}>
      <div style={{position: 'absolute', left: cx - d / 2, top: cy - d / 2, width: d, height: d, borderRadius: '50%',
        background: look.colors.accent, border: `${px(look, 12)}px solid ${look.tone.rim}`, boxShadow: `0 ${px(look, 8)}px ${px(look, 24)}px ${alpha(look.tone.matte, 0.3)}`,
        transform: `scale(${k}) rotate(${(right ? 1 : -1) * (12 - 6 * hash(seed + 2))}deg)`, display: 'flex', alignItems: 'center', justifyContent: 'center', boxSizing: 'border-box'}}>
        {text ? <Words text={text} family={look.display} size={fit(text.length, d * 0.72, px(look, 96), 0.5)} color={look.tone.rim} style={{textAlign: 'center'}} />
          : <Star d={d * 0.7} color={look.tone.rim} />}
      </div>
    </div>
  );
};

export default {Overlay, nudge} satisfies Move;
