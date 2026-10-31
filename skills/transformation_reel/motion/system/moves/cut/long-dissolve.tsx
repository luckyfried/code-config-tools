// long-dissolve: a long, slow veil of the card's dip while the camera drifts from one beat to the next, the way a film
// lets a scene go: the picture dims toward the dip and comes back, and is never lost. Into a wall that gives its posts,
// the posts rise under the veil and hand over to the wall itself by the window's end; into any other wall the veil lies
// over the scene itself.
import React from 'react';
import {clamp01, fill, SINE} from '../kit';
import {Incoming, opensOnto, standOf} from '../arrival';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, into, u}) => {
  const stand = into.form === 'wall' && opensOnto(look, into) ? standOf(u, 0.25) : 0;
  return (
    <>
      {stand > 0 ? <div style={{...fill, opacity: stand}}><Incoming look={look} into={into} rise={clamp01((u - 0.25) / 0.45)} /></div> : null}
      {look.tone.dip ? <div style={{...fill, background: look.tone.dip, opacity: 0.5 * SINE(Math.sin(Math.PI * u))}} /> : null}
    </>
  );
};

export default {beats: 3, jump: false, Overlay} satisfies Cut;
