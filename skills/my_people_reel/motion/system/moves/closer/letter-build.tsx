// letter-build: the closing line builds letter by letter on the card's first ink, which comes up over the last picture,
// each letter slamming in after the last, a word a line, the widest word filling the frame's width, in the card's
// accent; the letters come in across the whole of the closer and the last one lands on the stop, the handle comes up
// under it in the text face, and the whole block moves toward the viewer at an even rate until the stop.
import React from 'react';
import {alpha, fill, HANDLE, handleOn, land, measure, OUT, px, span, Words} from '../kit';
import type {CloserProps} from '../types';

const Closer: React.FC<CloserProps> = ({look, u}) => {
  const words = look.signoff.toUpperCase().split(/\s+/).filter(Boolean);
  const count = Math.max(1, words.join('').length);
  // a letter lands 0.7 of (2.5 per + 0.02) after it starts, so the last one lands on the stop
  const per = (1 - 0.7 * 0.02) / (count - 1 + 0.7 * 2.5);
  const pad = px(look, 60);
  // each letter is set on its own, with no kerning between letters, so the widest word is measured letter by letter,
  // and it fills the measure at the stop, where the block stands at full scale
  const wordW = (w: string) => [...w].reduce((sum, ch) => sum + measure(ch, look.display, 100, 800, 0) - 0.03 * 100, 0);
  const wide = (100 * (look.W - 2 * pad)) / Math.max(1, ...words.map(wordW));
  const size = Math.min(wide, (look.H * 0.6) / (words.length * 0.92));
  const hand = handleOn(look, look.colors.bg, look.colors.accent, 1);
  let n = 0;
  return (
    <div style={{...fill, background: alpha(look.colors.bg, span(u, 0, 0.2, OUT)), display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: pad, paddingBottom: look.H * 0.12, boxSizing: 'border-box'}}>
      <div style={{transform: `scale(${0.96 + 0.04 * span(u, 0, 1)})`, transformOrigin: '50% 50%'}}>
      {words.map((w, wi) => (
        <div key={wi} style={{display: 'flex', whiteSpace: 'pre', fontFamily: `'${look.display}'`, fontWeight: 800, fontSize: size, lineHeight: 0.92, color: look.colors.accent, letterSpacing: '-0.03em'}}>
          {[...w].map((ch, ci) => {
            const at = (n++) * per;
            const k = land(0.3 + (u - at) / (per * 2.5 + 0.02));
            return <span key={ci} style={{display: 'inline-block', opacity: u >= at ? 1 : 0, transform: `translateY(${(1 - k) * -size * 0.5}px) scale(${1.35 - 0.35 * k})`}}>{ch}</span>;
          })}
        </div>
      ))}
      {look.handle ? <Words text={look.handle} family={look.text} size={px(look, HANDLE)} color={hand.color}
        style={{marginTop: px(look, 48), fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', opacity: hand.opacity * span(u, 0.62, 0.25, OUT), transform: `translateY(${(1 - span(u, 0.62, 0.25, OUT)) * px(look, 30)}px)`}} /> : null}
      </div>
    </div>
  );
};

export default Closer;
