// bars-open: the frame opens from a slit: the letterbox bars, in the card's matte, part from near the middle to their
// resting height over the beat's first bars, the picture showing in the slit from the first frame.
import React from 'react';
import {fill, SINE, span} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, local}) => {
  const k = span(local, 0.1, 1.6, SINE);
  const bar = look.H * 0.42 * (1 - k);
  return (
    <div style={fill}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: bar, background: look.tone.matte}} />
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: bar, background: look.tone.matte}} />
    </div>
  );
};

export default {Overlay, nudge: ({u}) => ({scale: 1.04 - 0.04 * SINE(u)})} satisfies Move;
