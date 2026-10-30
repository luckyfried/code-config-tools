// page-drift: the picture lies on the page and drifts, sliding and turning a little as if pushed across a table, inside
// a margin of the card's ground with a torn foot.
import React from 'react';
import {fill, px, Window} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, u}) => {
  const m = px(look, 70);
  const tear = Array.from({length: 25}, (_, i) => `${(i / 24) * look.W},${look.H * 0.8 + ((i * 37) % 7) * px(look, 5)}`).join(' ');
  return (
    <div style={fill}>
      <Window box={[m, look.H * 0.12, look.W - 2 * m, look.H * 0.72]} color="transparent" rotate={-1.5 + 3 * u}
        style={{boxShadow: `0 0 0 6000px ${look.tone.ground}`}} />
      <svg width={look.W} height={look.H} style={{position: 'absolute', left: 0, top: 0}}>
        <polygon points={`0,${look.H} ${tear} ${look.W},${look.H}`} fill={look.tone.ground} />
      </svg>
    </div>
  );
};

export default {Overlay, nudge: ({u}) => ({dx: 0.05 * (u - 0.5), dy: -0.02 * u, roll: 0.03 * (u - 0.5)})} satisfies Move;
