// gate-weave: the frame weaves in the projector's gate, a small unsteady drift every frame, and the gate's soft rounded
// edges show around the picture in the card's matte.
import React from 'react';
import {alpha, fill, px, smoothNoise} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look}) => (
  <div style={{...fill, borderRadius: px(look, 70), boxShadow: `inset 0 0 ${px(look, 140)}px ${px(look, 40)}px ${alpha(look.tone.matte, 0.85)}`,
    outline: `${px(look, 30)}px solid ${look.tone.matte}`}} />
);

export default {
  Overlay,
  nudge: ({t, seed}) => ({dx: 0.006 * smoothNoise(t * 9, seed), dy: 0.009 * smoothNoise(t * 7, seed + 3), roll: 0.004 * smoothNoise(t * 5, seed + 7)}),
} satisfies Move;
