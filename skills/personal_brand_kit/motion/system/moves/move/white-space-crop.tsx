// white-space-crop: the picture set into a wide margin of the card's ground that opens around it as the beat begins,
// the beat's label in the display face's italic in the margin below, the way a magazine page leaves the photograph
// room.
import React from 'react';
import {fill, OUT, px, span, Window, Words} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local}) => {
  const m = span(local, 0, 0.9, OUT);
  // on the title the margin stays outside the type area (72 px left, 150 px right of 1080), so the title is never cut
  const side = beat.form === 'title' ? px(look, 40) : px(look, 70 + 50 * m), top = look.H * (0.12 + 0.04 * m), foot = look.H * (0.22 + 0.04 * m);
  return (
    <div style={fill}>
      <Window box={[side, top, look.W - 2 * side, look.H - top - foot]} color={look.tone.ground} />
      {beat.label ? (
        <Words text={beat.label} family={look.display} size={px(look, 64)} color={look.colors.ink}
          style={{position: 'absolute', left: side, top: look.H - foot + px(look, 40), fontStyle: look.italic ? 'italic' : 'normal', opacity: m}} />
      ) : null}
    </div>
  );
};

export default {Overlay} satisfies Move;
