// stack-and-split: two fields of the card's two inks closing in from the top and the bottom of the frame over the
// picture, the beat's label set large across the picture between them, and the fields splitting back out on the beat
// to give the picture the whole frame; the picture shows between them from the first frame.
import React from 'react';
import {fill, fitTo, land, px, Words} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local}) => {
  const open = land(Math.max(0, local - 0.15) * 1.4);
  const reach = look.H * 0.3 * (1 - open);
  const word = beat.label || beat.words.split(/\s+/)[0] || '';
  const size = word ? fitTo([word.toUpperCase()], look.display, look.W - px(look, 120), {weight: 800, most: px(look, 260)}) : 0;
  return (
    <div style={fill}>
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: reach, background: look.colors.bg}} />
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: reach, background: look.colors.accent}} />
      {word && open < 0.98 ? (
        <Words text={word.toUpperCase()} family={look.display} size={size} color={look.colors.bg}
          style={{position: 'absolute', left: 0, right: 0, top: look.H * 0.42 - size * 0.55, textAlign: 'center', fontWeight: 800, lineHeight: 1, opacity: 1 - open}} />
      ) : null}
    </div>
  );
};

export default {Overlay, nudge: ({u}) => ({scale: 1.06 - 0.06 * u})} satisfies Move;
