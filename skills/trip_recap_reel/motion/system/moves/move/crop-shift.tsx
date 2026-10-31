// crop-shift: the picture cropped one grid column narrower than its box on the card's ground, the crop jumping one
// column across halfway through the beat. The window's edges rest on the grid's column lines before and after the
// jump, and the camera kicks the same way as it jumps and settles back, so the words and the page never move off the
// grid.
import React from 'react';
import {fill, follow, heldOf, Mat, pictureOf, Window} from '../kit';
import type {Look, Move, MoveProps} from '../types';

/** The distance between two of the card's column lines, px. */
const pitch = (g: Look['grid']) => (g.cols[g.cols.length - 1] - g.cols[0]) / (g.cols.length - 1);

/** The camera's kick at the jump, as a share of the column pitch, and how fast it settles. */
const KICK = 0.12, SETTLE = 14;

const nudge = ({look, u}: MoveProps) => ({dx: u < 0.5 ? 0 : (KICK * pitch(look.grid) * Math.exp(-(u - 0.5) * SETTLE)) / look.H});

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, u, t} = p;
  const g = look.grid;
  const [bx, by, bw, bh] = beat.box ? pictureOf(look, beat) : [g.m, g.m, look.W - 2 * g.m, look.H - 2 * g.m];
  const col = pitch(g);
  const x = u < 0.5 ? bx : bx + col;
  return (
    <div style={{...fill, opacity: heldOf(beat, t), ...(beat.box ? follow(look, nudge(p)) : {})}}>
      {beat.box ? <Mat box={[bx, by, bw, bh]} inner={[x, by, bw - col, bh]} color={look.tone.ground} />
        : <Window box={[x, by, bw - col, bh]} color={look.tone.ground} />}
    </div>
  );
};

export default {Overlay, nudge} satisfies Move;
