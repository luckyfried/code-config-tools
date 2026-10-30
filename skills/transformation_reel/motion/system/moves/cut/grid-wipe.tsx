// grid-wipe: every other cell of the card's grid snaps shut in the card's ground in reading order, the cut happens
// under the checker, and the cells open again in the same order. Half the grid at most is ever shut, so the picture
// holds the other half.
import React from 'react';
import {clamp01, fill, SNAP} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) => {
  const {cols, rows} = look.grid;
  const nc = cols.length - 1, nr = rows.length - 1;
  const cells: React.ReactNode[] = [];
  for (let r = 0; r < nr; r++) {
    for (let c = 0; c < nc; c++) {
      if ((r + c) % 2) continue;
      const d = (r * nc + c) / (nr * nc) * 0.3;
      const k = SNAP(clamp01((u - d) / 0.2)) - SNAP(clamp01((u - 0.5 - d) / 0.2));
      if (k <= 0) continue;
      const x = cols[c], y = rows[r], w = cols[c + 1] - x, h = rows[r + 1] - y;
      cells.push(<div key={`${r}-${c}`} style={{position: 'absolute', left: x, top: y, width: w * k + 1, height: h + 1, background: look.tone.ground}} />);
    }
  }
  return <div style={fill}>{cells}</div>;
};

export default {beats: 1.4, jump: true, Overlay} satisfies Cut;
