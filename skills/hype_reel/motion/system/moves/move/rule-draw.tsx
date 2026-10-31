// rule-draw: a heavy rule of the card's accent drawn across the measure with a snap. On a beat with words the rule
// sits on a grid row and the words stand under it, flush left, set to fill the measure, the label in the text face over
// it, on the card's ground from the first frame. On a photo beat the rule draws across the photograph's head, between
// its words and its box, never through them, and a hairline closes its foot.
import React from 'react';
import {balance, fill, fitTo, heldOf, pictureOf, px, span, SNAP, Words} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local, t}) => {
  const g = look.grid;
  const left = g.cols[0], width = g.cols[g.cols.length - 1] - left;
  const d = 0.25 + 0.75 * span(local, 0, 0.5, SNAP);
  const heavy = px(look, 18);
  if (beat.box) {
    const [bx, by, bw, bh] = pictureOf(look, beat);
    const hair = Math.max(1, px(look, 3));
    // with the label and line set above the box, the rule stands in the middle of the space between their foot and the
    // box's head, and thins to fit it; with them below the box, the hairline does the same under the box
    const [, t0, , t1] = beat.type ?? [0, -1, 0, -1];
    const above = beat.type && t1 <= by, below = beat.type && t0 >= by + bh;
    const rule = above ? Math.min(heavy, (by - t1) * 0.5) : heavy;
    const ruleTop = above ? (t1 + by - rule) / 2 : by - heavy - px(look, 18);
    const hairTop = below ? (by + bh + t0 - hair) / 2 : by + bh + px(look, 14);
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
