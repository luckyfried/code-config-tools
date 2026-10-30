// polaroid-drop: the picture becomes an instant print on the page: a frame of the card's rim with a deep foot drops in
// turned at the card's tilt, lands with a small bounce, and the beat's label is written on its foot in the display face.
import React from 'react';
import {alpha, fill, hash, land, px, Window, Words} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local, seed}) => {
  const k = land(0.25 + local * 0.9);
  const tilt = look.print.tilt || -3;
  const title = beat.form === 'title';
  const turn = (title ? 0.5 : 1) * tilt * (0.6 + 0.4 * hash(seed + 1)) + 12 * (1 - k);
  // on the title the print is as wide as the frame allows, so its window holds the whole type area and the title is never cut
  const w = look.W * (title ? 0.96 : 0.78), h = w * 1.05, foot = w * 0.26;
  const rim = Math.max(look.print.rim, w * (title ? 0.035 : 0.05));
  const x = (look.W - w) / 2, y = look.H * 0.2 - (1 - k) * look.H * 0.5;
  return (
    <div style={fill}>
      <Window box={[x + rim, y + rim, w - 2 * rim, h - 2 * rim]} color="transparent" rotate={turn}
        style={{boxShadow: `0 0 0 ${rim}px ${look.tone.rim}, 0 ${foot}px 0 ${rim}px ${look.tone.rim}, 0 ${foot + px(look, 30)}px ${px(look, 60)}px ${rim}px ${alpha(look.tone.matte, 0.3)}, 0 0 0 6000px ${look.tone.ground}`}}>
        {beat.label || beat.words ? (
          <Words text={beat.label || beat.words} family={look.display} size={px(look, 76)} color={look.tone.pen}
            style={{position: 'absolute', left: 0, right: 0, top: h - 2 * rim + foot * 0.28, textAlign: 'center'}} />
        ) : null}
      </Window>
    </div>
  );
};

export default {Overlay} satisfies Move;
