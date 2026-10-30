// scale-to-cell: the picture's window steps in from its whole box to the box one grid column and one grid row smaller,
// anchored at its top left, on the card's ground; a block of the card's accent lands in the cell it gave up.
import React from 'react';
import {fill, heldOf, Mat, pictureOf, span, SNAP, Window} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, u, t}) => {
  const g = look.grid;
  const [bx, by, bw, bh] = beat.box ? pictureOf(look, beat) : [g.m, g.m, look.W - 2 * g.m, look.H - 2 * g.m];
  const col = (g.cols[g.cols.length - 1] - g.cols[0]) / (g.cols.length - 1);
  const row = (g.rows[g.rows.length - 1] - g.rows[0]) / (g.rows.length - 1);
  const k = span(u, 0.2, 0.35, SNAP);
  const w = bw - col * k, h = bh - row * 0.5 * k;
  const gap = col * 0.12;
  return (
    <div style={{...fill, opacity: heldOf(beat, t)}}>
      {beat.box ? <Mat box={[bx, by, bw, bh]} inner={[bx, by, w, h]} color={look.tone.ground} />
        : <Window box={[bx, by, w, h]} color={look.tone.ground} />}
      <div style={{position: 'absolute', left: bx + bw - col + gap, top: by + bh - col + gap, width: col - gap, height: col - gap,
        background: look.colors.accent, transform: `scale(${span(u, 0.45, 0.25, SNAP)})`, transformOrigin: '100% 100%'}} />
    </div>
  );
};

export default {Overlay} satisfies Move;
