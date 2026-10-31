// date-stamp: the beat's label burned into the corner of the type area in the text face, glowing in the card's accent
// the way a camcorder printed its date, blinking on as the beat begins. A beat with no label carries no stamp.
import React from 'react';
import {alpha, fill, px} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local}) => {
  if (!beat.label) return null;
  const on = local > 0.15 && (local > 0.6 || Math.floor(local * 8) % 2 === 0);
  return (
    <div style={fill}>
      <div style={{position: 'absolute', right: px(look, 120), bottom: look.H * 0.36, fontFamily: `'${look.text}'`, fontSize: px(look, 72),
        color: look.colors.accent, textShadow: `0 0 ${px(look, 12)}px ${look.colors.accent}, 0 0 2px ${alpha(look.tone.light, 0.9)}`, textTransform: 'uppercase',
        letterSpacing: '0.06em', opacity: on ? 0.95 : 0}}>{beat.label}</div>
    </div>
  );
};

export default {Overlay} satisfies Move;
