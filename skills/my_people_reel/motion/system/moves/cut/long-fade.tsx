// long-fade: the picture fades a long way toward the card's dip while the camera travels on, and the next beat comes
// up out of it, slowly; the veil is deeper and longer than a dissolve's, and the picture still reads through it.
import React from 'react';
import {fill, SINE} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) =>
  look.tone.dip ? <div style={{...fill, background: look.tone.dip, opacity: 0.62 * SINE(Math.sin(Math.PI * u))}} /> : null;

export default {beats: 2.4, jump: false, Overlay} satisfies Cut;
