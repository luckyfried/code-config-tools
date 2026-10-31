// grid-wipe: every other cell of the card's grid snaps shut in reading order, each a window onto the frame the cut
// opens onto (the incoming print on its ground, or the wall's posts), the cut happens under the checker, and the
// cells open again in the same order onto the incoming beat itself. Half the grid at most is ever shut, so the picture
// holds the other half. A cut into a beat with nothing to show shuts its cells in the card's ground.
import React from 'react';
import {clamp01, fill, SNAP} from '../kit';
import {Incoming, opensOnto} from '../arrival';
import type {Cut, CutProps} from '../types';

/** The shut cells at `u` through the window, each [x, y, w, h] px. */
export const shutAt = (grid: {cols: number[]; rows: number[]}, u: number) => {
  const {cols, rows} = grid;
  const nc = cols.length - 1, nr = rows.length - 1;
  const out: [number, number, number, number][] = [];
  for (let r = 0; r < nr; r++) {
    for (let c = 0; c < nc; c++) {
      if ((r + c) % 2) continue;
      const d = (r * nc + c) / (nr * nc) * 0.3;
      const k = SNAP(clamp01((u - d) / 0.2)) - SNAP(clamp01((u - 0.5 - d) / 0.2));
      if (k <= 0) continue;
      const x = cols[c], y = rows[r], w = cols[c + 1] - x, h = rows[r + 1] - y;
      out.push([x, y, w * k + 1, h + 1]);
    }
  }
  return out;
};

const Overlay: React.FC<CutProps> = ({look, into, u}) => {
  const shut = shutAt(look.grid, u);
  if (!shut.length) return null;
  if (!opensOnto(look, into)) {
    return <div style={fill}>{shut.map(([x, y, w, h], i) => <div key={i} style={{position: 'absolute', left: x, top: y, width: w, height: h, background: look.tone.ground}} />)}</div>;
  }
  const path = shut.map(([x, y, w, h]) => `M ${x} ${y} h ${w} v ${h} h ${-w} Z`).join(' ');
  return (
    <div style={{...fill, overflow: 'hidden', clipPath: `path('${path}')`}}>
      <Incoming look={look} into={into} />
    </div>
  );
};

export default {beats: 1.4, jump: true, Overlay} satisfies Cut;
