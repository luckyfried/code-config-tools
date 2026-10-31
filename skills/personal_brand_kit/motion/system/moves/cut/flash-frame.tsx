// flash-frame: a hard cut through a flash of the card's light: two frames at its height, the picture still in it, then
// gone over the next few.
import React from 'react';
import {fill} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) => {
  // the window is half a musical beat; the flash peaks on the two frames either side of the cut
  const frames = (u - 0.5) * 0.5 * look.pulse;
  const a = frames < -1 ? 0 : frames < 1 ? 0.7 : 0.7 * Math.max(0, 1 - (frames - 1) / 3);
  return <div style={{...fill, background: look.tone.light, opacity: a, mixBlendMode: 'screen'}} />;
};

export default {beats: 0.5, jump: true, Overlay} satisfies Cut;
