// long-dissolve: a long, slow veil of the card's dip while the camera drifts from one beat to the next, the way a film
// lets a scene go: the picture dims toward the dip and comes back, and is never lost.
import React from 'react';
import {fill, SINE} from '../kit';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, u}) =>
  look.tone.dip ? <div style={{...fill, background: look.tone.dip, opacity: 0.5 * SINE(Math.sin(Math.PI * u))}} /> : null;

export default {beats: 3, jump: false, Overlay} satisfies Cut;
