// doodle-draw-on: a pen in the card's hand ink draws on the page. On a photo beat it scribbles a loop around the
// print's corner and a little arrow toward it, clear of the words the card sets under the print, while the page
// drifts. On a beat with words it writes them large in the display face on the card's ground, there from the first
// frame, and the pen underlines them and loops the label.
import React from 'react';
import {balance, fill, fitTo, follow, hash, heldOf, pictureOf, px, span, Words} from '../kit';
import type {Move, MoveProps} from '../types';

const nudge = ({u}: {u: number}) => ({dx: -0.01 * (u - 0.5), dy: -0.005 * u, roll: -0.005 * (u - 0.5)});
const LEN = 4000;

const Pen: React.FC<{d: string; look: MoveProps['look']; k: number; w?: number}> = ({d, look, k, w = 10}) => (
  <path d={d} fill="none" stroke={look.tone.pen} strokeWidth={px(look, w)} strokeLinecap="round" strokeLinejoin="round"
    strokeDasharray={LEN} strokeDashoffset={LEN * (1 - k)} />
);

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, local, seed, t} = p;
  const draw = span(local, 0.05, 1.3);
  if (beat.box) {
    const [bx, by, bw] = pictureOf(look, beat);
    const left = hash(seed) > 0.5;
    const r = px(look, 110), edge = r * 2.1;
    const cx = Math.min(look.W - edge, Math.max(edge, left ? bx : bx + bw)), cy = Math.max(r * 1.6, by), s = left ? -1 : 1;
    const loop = `M ${cx - s * r * 1.1} ${cy + r * 0.2} C ${cx - s * r * 1.2} ${cy - r * 1.3}, ${cx + s * r * 1.3} ${cy - r * 1.2}, ${cx + s * r * 1.05} ${cy + r * 0.1} S ${cx - s * r * 0.4} ${cy + r * 1.1}, ${cx - s * r * 0.9} ${cy - r * 0.2}`;
    const ax = cx + s * r * 1.9, ay = cy - r * 1.4;
    const arrow = `M ${ax} ${ay} Q ${ax - s * r * 0.2} ${ay + r * 0.7}, ${cx + s * r * 1.15} ${cy - r * 0.55} M ${cx + s * r * 1.15} ${cy - r * 0.55} l ${s * r * 0.36} ${-r * 0.06} M ${cx + s * r * 1.15} ${cy - r * 0.55} l ${s * r * 0.08} ${-r * 0.36}`;
    return (
      <div style={{...fill, opacity: heldOf(beat, t), ...follow(look, nudge(p))}}>
        <svg width={look.W} height={look.H} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible'}}>
          <Pen d={loop} look={look} k={span(draw, 0, 0.6)} />
          <Pen d={arrow} look={look} k={span(draw, 0.55, 0.45)} w={8} />
        </svg>
      </div>
    );
  }
  const text = beat.words || beat.label;
  if (!text) return null;
  const lines = balance(text, text.length > 18 ? 3 : 2);
  const left = px(look, 110), width = look.W - 2 * left;
  const size = fitTo(lines, look.display, width, {most: px(look, 190)});
  const top = look.H * 0.44 - (lines.length * size) / 2;
  const foot = top + lines.length * size + px(look, 20);
  const under = `M ${left} ${foot} q ${width * 0.45} ${px(look, -26)} ${width * 0.95} ${px(look, 8)}`;
  const label = beat.label && beat.label !== text ? beat.label : '';
  const lx = left + px(look, 20), ly = top - px(look, 90);
  const ring = `M ${lx - px(look, 30)} ${ly + px(look, 30)} c ${px(look, -10)} ${px(look, -80)}, ${px(look, 340)} ${px(look, -80)}, ${px(look, 330)} ${px(look, 0)} s ${px(look, -300)} ${px(look, 70)}, ${px(look, -320)} ${px(look, -10)}`;
  return (
    <div style={{...fill, background: look.tone.ground}}>
      {label ? <Words text={label} family={look.text} size={px(look, 44)} color={look.colors.accent} style={{position: 'absolute', left: lx, top: ly - px(look, 30)}} /> : null}
      <Words text={lines.join('\n')} family={look.display} size={size} color={look.colors.ink}
        style={{position: 'absolute', left, width, top, lineHeight: 1, transform: `rotate(-2deg) translateY(${(1 - span(local, 0, 0.5)) * px(look, 14)}px)`}} />
      <svg width={look.W} height={look.H} style={{position: 'absolute', left: 0, top: 0}}>
        <Pen d={under} look={look} k={span(draw, 0.2, 0.5)} />
        {label ? <Pen d={ring} look={look} k={span(draw, 0.5, 0.5)} w={7} /> : null}
      </svg>
    </div>
  );
};

export default {Overlay, nudge} satisfies Move;
