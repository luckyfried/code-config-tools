// rule-draw: a heavy rule of the card's accent drawn across the measure with a snap. On a beat with words the rule
// sits on a grid row and the words stand under it, flush left, set to fill the measure, the label in the text face over
// it, on the card's ground from the first frame. On a photo beat the rule draws across the photograph's head, in the
// space between its words and its box, and a hairline closes its foot; where that space is too narrow to hold the rule
// clear of both, or the frame's edge leaves none, the rule draws just inside the photograph's head and the hairline
// just inside its foot, so neither ever crosses a word or leaves the frame.
import React from 'react';
import {balance, fill, fitTo, heldOf, pictureOf, px, span, SNAP, Words} from '../kit';
import type {Look, Move, MoveProps} from '../types';

/** The rule's and hairline's bands on a photograph standing in `box`, with the beat's label and line in `type`
 * ([x0, y0, x1, y1] px): [top, height] of each. */
export const rulesOf = (look: Look, [, by, , bh]: [number, number, number, number], type?: [number, number, number, number]) => {
  const heavy = px(look, 18), hair = Math.max(1, px(look, 3)), pad = px(look, 14), least = px(look, 6);
  const [, t0, , t1] = type ?? [0, -1, 0, -1];
  // the free space over the box's head and under its foot: to the words where they stand there, and a mark stands in
  // the middle of it; else to the frame's edge, and a mark stands `pad` off the box
  const above = !!type && t1 <= by, below = !!type && t0 >= by + bh;
  const over = above ? by - t1 : by;
  const under = below ? t0 - by - bh : look.H - by - bh;
  const rule = Math.min(heavy, above ? (over - 2 * least) / 2 : over - 2 * least);
  const ruleGap = above ? (over - rule) / 2 : Math.min(pad, (over - rule) / 2);
  const ruleBand: [number, number] = rule >= least ? [by - ruleGap - rule, rule] : [by + pad, heavy];
  const hairGap = below ? (under - hair) / 2 : Math.min(pad, (under - hair) / 2);
  const hairBand: [number, number] = under >= hair + 2 * least ? [by + bh + hairGap, hair] : [by + bh - pad - hair, hair];
  return {rule: ruleBand, hair: hairBand};
};

const Overlay: React.FC<MoveProps> = ({look, beat, local, t}) => {
  const g = look.grid;
  const left = g.cols[0], width = g.cols[g.cols.length - 1] - left;
  const d = 0.25 + 0.75 * span(local, 0, 0.5, SNAP);
  const heavy = px(look, 18);
  if (beat.box) {
    const [bx, by, bw, bh] = pictureOf(look, beat);
    const {rule: [ruleTop, rule], hair: [hairTop, hair]} = rulesOf(look, [bx, by, bw, bh], beat.type);
    return (
      <div style={{...fill, opacity: heldOf(beat, t)}}>
        <div style={{position: 'absolute', left: bx, top: ruleTop, height: rule, width: bw * d, background: look.colors.accent}} />
        <div style={{position: 'absolute', left: bx + bw * (1 - d), top: hairTop, height: hair, width: bw * d, background: look.colors.ink}} />
      </div>
    );
  }
  const text = beat.words || beat.label;
  if (!text) return null;
  const lines = balance(text, text.length > 16 ? 3 : text.length > 8 ? 2 : 1);
  const size = fitTo(lines, look.display, width, {weight: 700, tracking: -0.03, most: px(look, 210)});
  const y = g.rows[Math.min(2, g.rows.length - 1)];
  return (
    <div style={{...fill, background: look.tone.ground}}>
      <div style={{position: 'absolute', left, top: y, height: heavy, width: width * d, background: look.colors.accent}} />
      {beat.label && beat.label !== text ? <Words text={beat.label} family={look.text} size={px(look, 34)} color={look.colors.ink} style={{position: 'absolute', left, top: y - px(look, 60)}} /> : null}
      <Words text={lines.join('\n')} family={look.display} size={size} color={look.colors.ink}
        style={{position: 'absolute', left, width, top: y + px(look, 50), letterSpacing: '-0.03em', lineHeight: 0.98, fontWeight: 700,
          transform: `translateY(${(1 - span(local, 0, 0.4, SNAP)) * px(look, 24)}px)`}} />
    </div>
  );
};

export default {Overlay} satisfies Move;
