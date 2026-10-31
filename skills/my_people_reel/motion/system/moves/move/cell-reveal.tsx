// cell-reveal: the photograph comes on through the card's grid: the cells of its box, held back in a checker (the
// photograph in them grey and dimmed), come up to its full color one after another in reading order as it opens, the
// held-back face lifting off each cell, until the photograph has its box whole. The open cells show the photograph from
// the first frame. The cells are the card's grid cells inside the photograph's box, held back while the camera holds
// on it, and gone before the pull back to the wall, so no cell stands off its place.
import React from 'react';
import {alpha, clamp01, fill, heldOf, pictureOf, SNAP} from '../kit';
import {Face} from '../arrival';
import type {Move, MoveProps} from '../types';

/** How a cell not yet revealed holds the photograph back. */
export const HELD_BACK = 'grayscale(0.9) brightness(0.62)';

const Overlay: React.FC<MoveProps> = ({look, beat, local, t}) => {
  if (!beat.box) return null;
  const [bx, by, bw, bh] = pictureOf(look, beat);
  const g = look.grid;
  const src = beat.photo;
  const place = beat.place;
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
      // the photograph itself, held back, where the shot lays it; without its address, the picture behind, held back
      cells.push(
        <div key={`${r}-${c}`} style={{position: 'absolute', left: x, top: y, width: w, height: h * k, overflow: 'hidden',
          backdropFilter: src ? undefined : HELD_BACK}}>
          {src ? (
            <div style={{position: 'absolute', left: bx - x, top: by - y, filter: HELD_BACK}}>
              <Face src={src} w={bw} h={bh} place={place ? [place[0] - bx, place[1] - by, place[2], place[3]] : undefined} />
            </div>
          ) : null}
          <div style={{position: 'absolute', inset: 0, background: alpha(look.tone.ground, 0.12)}} />
        </div>,
      );
    }
  }
  return <div style={{...fill, opacity: heldOf(beat, t)}}>{cells}</div>;
};

export default {Overlay} satisfies Move;
