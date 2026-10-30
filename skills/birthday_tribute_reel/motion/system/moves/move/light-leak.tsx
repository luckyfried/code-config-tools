// light-leak: light leaking into the camera at the frame's edges: warm glows of the card's light and accent bloom in
// from a corner and the opposite side and drift along the edge, the middle of the frame, where the subject is, left
// clear.
import React from 'react';
import {alpha, fill, smoothNoise, span} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, local, u, seed}) => {
  const a = span(local, 0, 0.8) * (0.5 + 0.3 * smoothNoise(local * 2, seed));
  const y = 10 + 30 * u;
  return (
    <div style={{...fill, mixBlendMode: 'screen', opacity: a,
      background: `radial-gradient(ellipse 45% 30% at -6% ${y}%, ${alpha(look.tone.light, 0.95)} 0%, ${alpha(look.colors.accent, 0.5)} 45%, transparent 100%), radial-gradient(ellipse 30% 40% at 106% ${100 - y}%, ${alpha(look.colors.accent, 0.8)} 0%, transparent 100%)`}} />
  );
};

export default {Overlay} satisfies Move;
