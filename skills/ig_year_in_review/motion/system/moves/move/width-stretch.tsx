// width-stretch: the beat's label in the text face across a band of the card's accent, stretched from a sliver until
// it spans the band, never past the frame's edge.
import React from 'react';
import {fill, measure, px, span, SNAP, Words, wordsOf} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, u}) => {
  const word = (beat.label || wordsOf(beat.words).slice(0, 2).join(' ')).toUpperCase();
  if (!word) return null;
  const band = px(look, 300);
  const size = band * 0.86;
  const most = (look.W - px(look, 80)) / Math.max(1, measure(word, look.text, size));
  const sx = Math.min(most, 0.25 + 1.6 * span(u, 0, 1, SNAP));
  return (
    <div style={fill}>
      <div style={{position: 'absolute', left: 0, right: 0, top: look.H * 0.5, height: band, background: look.colors.accent,
        display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden'}}>
        <Words text={word} family={look.text} size={size} color={look.colors.bg} style={{transform: `scaleX(${sx})`, whiteSpace: 'nowrap'}} />
      </div>
    </div>
  );
};

export default {Overlay} satisfies Move;
