// poster: the film ends as a printed poster on the card's ground, laid on the card's grid: a heavy rule in the ink
// snapping across the measure, the film's title set big and flush left in the display face across the measure, the
// closing line under it in the text face, one block of the card's accent filling a grid cell, the handle at the foot,
// the title standing on the ground from the closer's first frame, the rest laid in turn across the closer, the block
// landing on the stop.
import React from 'react';
import {balance, fill, fitTo, HANDLE, handleOn, inkOn, OUT, px, SNAP, span, Words} from '../kit';
import type {CloserProps} from '../types';

const Closer: React.FC<CloserProps> = ({look, u}) => {
  const g = look.grid;
  const ink = inkOn(look.tone.ground, [look.colors.ink, look.colors.paper]);
  const hand = handleOn(look, look.tone.ground, ink, 1);
  const measureW = look.W - 2 * g.m;
  const title = look.title || look.signoff;
  const lines = balance(title, title.length > 12 ? 2 : 1);
  const said = look.title ? balance(look.signoff, look.signoff.length > 24 ? 2 : 1) : [];
  const saidSize = said.length ? Math.min(px(look, 66), fitTo(said, look.text, measureW * 0.75)) : 0;
  const r = 0.25 + 0.75 * span(u, 0, 0.3, SNAP);
  const row = (i: number) => g.rows[Math.min(g.rows.length - 1, i)];
  const col = (i: number) => g.cols[Math.min(g.cols.length - 1, i)];
  const top = row(1) + px(look, 60);
  // the title spans the measure, and the title and the closing line stand clear of the last row, whatever the format
  const room = row(g.rows.length - 2) - top - (said.length ? said.length * saidSize * 1.2 + px(look, 50) : 0) - px(look, 30);
  const size = Math.min(fitTo(lines, look.display, measureW, {weight: 700, tracking: -0.035, most: px(look, 300)}), room / (lines.length * 0.95));
  return (
    <div style={{...fill, background: look.tone.ground}}>
      <div style={{position: 'absolute', left: g.m, top: row(1), width: measureW * r, height: px(look, 22), background: ink}} />
      <Words text={lines.join('\n')} family={look.display} size={size} color={ink}
        style={{position: 'absolute', left: g.m - size * 0.04, top, lineHeight: 0.95, fontWeight: 700, letterSpacing: '-0.035em', whiteSpace: 'pre', transform: `translateY(${(1 - span(u, 0, 0.3, SNAP)) * px(look, 30)}px)`}} />
      {said.length ? <Words text={said.join('\n')} family={look.text} size={saidSize} color={ink}
        style={{position: 'absolute', left: g.m, top: top + lines.length * size * 0.95 + px(look, 50), lineHeight: 1.2, opacity: span(u, 0.2, 0.25)}} /> : null}
      <div style={{position: 'absolute', left: col(g.cols.length - 2), top: row(g.rows.length - 2), width: col(g.cols.length - 1) - col(g.cols.length - 2), height: row(g.rows.length - 1) - row(g.rows.length - 2), background: look.colors.accent,
        transform: `scaleY(${span(u, 0.4, 0.6, OUT)})`, transformOrigin: 'top'}} />
      {look.handle ? <Words text={look.handle} family={look.text} size={px(look, HANDLE)} color={hand.color} style={{position: 'absolute', left: g.m, top: row(g.rows.length - 2), opacity: hand.opacity * span(u, 0.45, 0.3)}} /> : null}
    </div>
  );
};

export default Closer;
