// caption-alone: the film ends on the card's ground with the closing line alone, set across the measure in the display
// face's italic like a caption under a photograph that is no longer there, the handle under it in the text face; the
// line rises across the closer and settles on the stop.
import React from 'react';
import {balance, fill, fitTo, HANDLE, handleOn, inkOn, OUT, px, span, Words} from '../kit';
import type {CloserProps} from '../types';

const Closer: React.FC<CloserProps> = ({look, u}) => {
  const a = span(u, 0, 0.6, OUT);
  const b = span(u, 0, 0.8, OUT);
  const side = px(look, 120), width = look.W - 2 * side;
  const lines = balance(look.signoff, look.signoff.length > 14 ? 2 : 1);
  const size = Math.min(fitTo(lines, look.display, width, {most: px(look, 170)}), (look.H * 0.4) / (lines.length * 1.08));
  const ink = inkOn(look.tone.ground, [look.colors.ink, look.colors.paper]);
  const top = look.H * 0.5 - lines.length * size * 0.55;
  const hand = handleOn(look, look.tone.ground, ink, 0.72);
  return (
    <div style={fill}>
      <div style={{...fill, background: look.tone.ground, opacity: a}} />
      <Words text={lines.join('\n')} family={look.display} size={size} color={ink}
        style={{position: 'absolute', left: side, top, lineHeight: 1.08, fontStyle: look.italic ? 'italic' : 'normal', whiteSpace: 'pre', opacity: 0.25 + 0.75 * b, transform: `translateY(${(1 - b) * px(look, 24)}px)`}} />
      {look.handle ? <Words text={look.handle} family={look.text} size={px(look, HANDLE)} color={hand.color}
        style={{position: 'absolute', left: side, top: top + lines.length * size * 1.08 + px(look, 60), letterSpacing: '0.14em', textTransform: 'uppercase', opacity: hand.opacity * span(u, 0.4, 0.4, OUT)}} /> : null}
    </div>
  );
};

export default Closer;
