// slide: a flat panel of the card's accent wipes across the frame with a smear, and the next beat is there behind it;
// the panel is narrower than the frame, so the picture is never gone.
import React from 'react';
import {fill, SNAP} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) => {
  const w = look.W * 0.55;
  const x = -w + SNAP(u) * (look.W + w);
  return <div style={fill}><div style={{position: 'absolute', top: 0, bottom: 0, left: x, width: w, background: look.colors.accent, transform: 'skewX(-8deg)'}} /></div>;
};

export default {beats: 1, jump: true, Overlay, fx: ({u}) => ({smear: [0.05 * Math.sin(Math.PI * u), 0] as [number, number]})} satisfies Cut;
