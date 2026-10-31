// crop-shift: the picture cropped one grid column narrower than its box on the card's ground, the crop jumping one
// column across halfway through the beat. The column is a column of the box the picture stands in (cellOf), so the
// window's edges rest on the box's column lines before and after the jump, and the camera kicks the same way as it
// jumps and settles back, so the words and the page never move off the grid.
import React from 'react';
import {cellOf, fill, follow, heldOf, Mat, pictureOf, Window} from '../kit';
import type {Move, MoveProps} from '../types';

/** The camera's kick at the jump, as a share of the column pitch, and how fast it settles. */
const KICK = 0.12, SETTLE = 14;

const nudge = ({look, beat, u}: MoveProps) => ({dx: u < 0.5 ? 0 : (KICK * cellOf(look, beat).col * Math.exp(-(u - 0.5) * SETTLE)) / look.H});

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, u, t} = p;
  const g = look.grid;
  const [bx, by, bw, bh] = beat.box ? pictureOf(look, beat) : [g.m, g.m, look.W - 2 * g.m, look.H - 2 * g.m];
  const {col} = cellOf(look, beat);
  const x = u < 0.5 ? bx : bx + col;
  return (
    <div style={{...fill, opacity: heldOf(beat, t), ...(beat.box ? follow(look, nudge(p)) : {})}}>
      {beat.box ? <Mat box={[bx, by, bw, bh]} inner={[x, by, bw - col, bh]} color={look.tone.ground} />
        : <Window box={[x, by, bw - col, bh]} color={look.tone.ground} />}
    </div>
  );
};

export default {Overlay, nudge} satisfies Move;
