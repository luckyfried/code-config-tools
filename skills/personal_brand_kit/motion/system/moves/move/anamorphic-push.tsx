// anamorphic-push: a slow push in, with the long horizontal streak an anamorphic lens draws from a light at the frame's
// edge: in the card's light, high in the frame under the bar and rising off the side, never across the subject.
import React from 'react';
import {alpha, fill, px, SINE, span} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, local, u}) => {
  const a = span(local, 0.3, 1.2) * (1 - span(u, 0.8, 0.2));
  const y = look.H * (0.17 - 0.015 * u);
  const L = look.tone.light;
  return (
    <div style={{...fill, mixBlendMode: 'screen', opacity: a}}>
      <div style={{position: 'absolute', left: -look.W * 0.1, width: look.W * 1.2, top: y - px(look, 4), height: px(look, 8),
        background: `linear-gradient(to right, ${alpha(L, 0.95)}, ${alpha(L, 0.5)} 30%, ${alpha(L, 0.12)} 65%, transparent)`, filter: `blur(${px(look, 3)}px)`}} />
      <div style={{position: 'absolute', left: -px(look, 160), top: y - px(look, 160), width: px(look, 320), height: px(look, 320), borderRadius: '50%',
        background: `radial-gradient(circle, ${alpha(L, 0.55)}, transparent 70%)`}} />
    </div>
  );
};

export default {Overlay, nudge: ({u}) => ({scale: 1 - 0.1 * SINE(u)})} satisfies Move;
