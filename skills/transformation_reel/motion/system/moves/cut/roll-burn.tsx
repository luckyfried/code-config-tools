// roll-burn (the cut): the film burns through at the end of one shot: the burn runs in from the frame's edge in the
// card's burn color, a warm glow of the card's light washes over the picture without whiting it out, and the next shot
// runs in out of it.
import React from 'react';
import {fill, SINE} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) => {
  const a = SINE(Math.sin(Math.PI * u));
  return (
    <div style={{...fill, mixBlendMode: 'screen', opacity: 0.6 * a,
      background: `radial-gradient(ellipse 80% 120% at 0% 50%, ${look.tone.light} 0%, transparent 75%)`}} />
  );
};

export default {beats: 1.6, jump: true, Overlay, fx: ({u}) => ({burn: 0.7 * Math.sin(Math.PI * u)})} satisfies Cut;
