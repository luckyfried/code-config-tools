// diptych: the picture split into two panels by a gutter of the card's ground down its middle and framed in the same
// ground, the right panel settling a moment after the left.
import React from 'react';
import {fill, OUT, px, span} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, local}) => {
  const m = span(local, 0, 0.8, OUT);
  const edge = px(look, 60), gutter = px(look, 10 + 26 * m);
  const ground = look.tone.ground;
  return (
    <div style={fill}>
      <div style={{...fill, border: `${edge}px solid ${ground}`, borderTopWidth: look.H * 0.14, borderBottomWidth: look.H * 0.14}} />
      <div style={{position: 'absolute', top: 0, bottom: 0, left: look.W / 2 - gutter / 2, width: gutter, background: ground}} />
    </div>
  );
};

export default {Overlay, nudge: ({u}) => ({dx: 0.015 * (u - 0.5)})} satisfies Move;
