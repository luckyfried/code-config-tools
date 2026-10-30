// cell-reveal: the photograph comes on through the card's grid: the cells of its box shut in a checker of the card's
// ground lift away one after another in reading order as it opens, until the photograph has its box whole. The open
// cells show the photograph from the first frame. The blocks are the card's grid cells inside the photograph's box,
// lifted while the camera holds on it, and gone before the pull back to the wall, so no block stands off its cell.
import React from 'react';
import {clamp01, fill, heldOf, pictureOf, SNAP} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local, t}) => {
  if (!beat.box) return null;
  const [bx, by, bw, bh] = pictureOf(look, beat);
  const g = look.grid;
  // the grid's lines inside the box, with the box's own edges
  const xs = [bx, ...g.cols.filter((x) => x > bx + 4 && x < bx + bw - 4), bx + bw];
  const ys = [by, ...g.rows.filter((y) => y > by + 4 && y < by + bh - 4), by + bh];
  const cells: React.ReactNode[] = [];
  let n = 0;
  for (let r = 0; r + 1 < ys.length; r++) {
    for (let c = 0; c + 1 < xs.length; c++) {
      if ((r + c) % 2) continue;
      const k = 1 - SNAP(clamp01((local - 0.2 - n * 0.07) / 0.25));
      n += 1;
      if (k <= 0) continue;
      const x = xs[c], y = ys[r], w = xs[c + 1] - x, h = ys[r + 1] - y;
      cells.push(<div key={`${r}-${c}`} style={{position: 'absolute', left: x - 0.5, top: y - 0.5, width: w + 1, height: h * k + 1, background: look.tone.ground}} />);
    }
  }
  return <div style={{...fill, opacity: heldOf(beat, t)}}>{cells}</div>;
};

export default {Overlay} satisfies Move;
