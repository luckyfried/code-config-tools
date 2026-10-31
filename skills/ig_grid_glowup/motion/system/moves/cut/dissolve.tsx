// dissolve: one beat gives way to the next through a soft veil of the card's dip while the camera travels, the veil
// at its thickest at the cut and never so thick that the picture goes. A light dip washes a photograph toward grey, so
// on a light dip the veil is thinner and lies only over the middle half of the window, and the picture keeps its
// color on either side of the cut; a card that never dips travels with no veil.
import React from 'react';
import {clamp01, fill, lumOf, SINE} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) => {
  const dip = look.tone.dip;
  if (!dip) return null;
  const light = lumOf(dip) > 0.5;
  const k = light ? SINE(clamp01(1 - Math.abs(u - 0.5) / 0.25)) : SINE(Math.sin(Math.PI * u));
  return <div style={{...fill, background: dip, opacity: (light ? 0.22 : 0.45) * k}} />;
};

export default {beats: 1.2, jump: false, Overlay} satisfies Cut;
