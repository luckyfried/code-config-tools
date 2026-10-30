// page-turn: a page turns over the frame: a leaf of the card's ground, its fold shadowed and its edge lit, sweeps across
// on a slant while the camera travels to the next beat under it. The leaf is narrower than the frame, so the picture
// shows on one side of it or the other on every frame.
import React from 'react';
import {alpha, fill, px, SINE} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) => {
  const k = SINE(u);
  const w = look.W * 0.62;
  // the leaf narrows as it lifts past the middle, the way a page foreshortens as it stands up
  const lift = Math.sin(Math.PI * k);
  const leaf = w * (1 - 0.45 * lift);
  const x = look.W * 1.1 - k * (look.W * 1.2 + w);
  return (
    <div style={{...fill, overflow: 'hidden'}}>
      <div style={{position: 'absolute', top: -look.H * 0.15, height: look.H * 1.3, left: x, width: leaf, background: look.tone.ground,
        transform: 'rotate(8deg)', boxShadow: `${px(look, -30)}px 0 ${px(look, 50)}px ${alpha(look.tone.matte, 0.32)}, ${px(look, 24)}px 0 ${px(look, 40)}px ${alpha(look.tone.matte, 0.18)}`,
        backgroundImage: `linear-gradient(to right, ${alpha(look.tone.matte, 0.16 * (1 - lift))}, transparent ${px(look, 80)}px, transparent 70%, ${alpha(look.tone.light, 0.18)})`}} />
    </div>
  );
};

export default {beats: 1.4, jump: false, Overlay} satisfies Cut;
