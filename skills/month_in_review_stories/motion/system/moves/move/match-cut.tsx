// match-cut: the picture opens out of a circle at the frame's middle, the same circle the beat before closed on, so the
// two shapes match across the cut; outside the circle, the card's matte.
import React from 'react';
import {fill, SINE, span} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, local}) => {
  const r = Math.hypot(look.W, look.H) * (0.28 + 0.3 * span(local, 0, 1.2, SINE));
  return (
    <div style={{...fill, background: `radial-gradient(circle at 50% 50%, transparent ${r}px, ${look.tone.matte} ${r + 2}px)`}} />
  );
};

export default {Overlay} satisfies Move;
