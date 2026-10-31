// dissolve: one beat gives way to the next through a soft veil of the card's dip while the camera travels, the veil
// at its thickest at the cut and never so thick that the picture goes. A light dip washes a photograph toward grey, so
// on a light dip the veil is thinner and lies only over the middle half of the window, and the picture keeps its
// color on either side of the cut; a card that never dips travels with no veil. Into a wall that gives its posts, the
// posts rise under the veil as the camera pulls back and hand over to the wall itself by the window's end; into any other
// wall the veil lies over the scene itself.
import React from 'react';
import {clamp01, fill, lumOf, SINE} from '../kit';
import {Incoming, opensOnto, standOf} from '../arrival';
import type {Cut, CutProps} from '../types';

const Overlay: React.FC<CutProps> = ({look, into, u}) => {
  const dip = look.tone.dip;
  const stand = into.form === 'wall' && opensOnto(look, into) ? standOf(u, 0.2) : 0;
  const light = dip ? lumOf(dip) > 0.5 : false;
  const k = light ? SINE(clamp01(1 - Math.abs(u - 0.5) / 0.25)) : SINE(Math.sin(Math.PI * u));
  return (
    <>
      {stand > 0 ? <div style={{...fill, opacity: stand}}><Incoming look={look} into={into} rise={clamp01((u - 0.2) / 0.5)} /></div> : null}
      {dip ? <div style={{...fill, background: dip, opacity: (light ? 0.22 : 0.45) * k}} /> : null}
    </>
  );
};

export default {beats: 1.2, jump: false, Overlay} satisfies Cut;
