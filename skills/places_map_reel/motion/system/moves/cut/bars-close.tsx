// bars-close: the letterbox bars close in the card's matte to a slit over the cut, the shot carried on in the slit, and
// open again on the next shot.
import React from 'react';
import {fill, SINE} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) => {
  const bar = look.H * 0.4 * SINE(Math.sin(Math.PI * u));
  return (
    <div style={fill}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: bar, background: look.tone.matte}} />
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: bar, background: look.tone.matte}} />
    </div>
  );
};

export default {beats: 2, jump: true, Overlay} satisfies Cut;
