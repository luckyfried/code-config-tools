// long-fade-title: the beat's words stand in the display face's capitals on the card's ground, centred, the spacing
// opening slowly while the light on them comes up and settles, the way a film sets a title over a held shot. A beat
// with no words of its own dims the picture a little toward the card's dip and lets it come back.
import React from 'react';
import {alpha, balance, fill, fitTo, px, SINE, span, Words} from '../kit';
import type {Move, MoveProps} from '../types';

const Overlay: React.FC<MoveProps> = ({look, beat, local, u}) => {
  const text = beat.words || beat.label;
  if (!text) {
    const veil = 0.3 * Math.sin(Math.PI * u);
    return look.tone.dip ? <div style={{...fill, background: look.tone.dip, opacity: veil}} /> : null;
  }
  const lines = balance(text.toUpperCase(), text.length > 18 ? 3 : text.length > 9 ? 2 : 1);
  const spread = 0.1 + 0.08 * SINE(u);
  const size = fitTo(lines, look.display, look.W - 2 * px(look, 110), {tracking: 0.18, most: px(look, 150)});
  const light = 0.72 + 0.28 * span(local, 0, 1.2, SINE);
  return (
    <div style={{...fill, background: look.colors.bg, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{...fill, background: `radial-gradient(ellipse 70% 40% at 50% 50%, ${alpha(look.tone.light, 0.08)}, transparent 70%)`}} />
      <Words text={lines.join('\n')} family={look.display} size={size} color={look.colors.paper}
        style={{opacity: light, textAlign: 'center', letterSpacing: `${spread}em`, lineHeight: 1.18, position: 'relative'}} />
    </div>
  );
};

export default {Overlay} satisfies Move;
