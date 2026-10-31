// letter-build: the closing line builds letter by letter on the card's first ink, which comes up over the last picture,
// each letter slamming in after the last, about two words a line so a short word never stands alone, the widest line
// filling the profile's safe width, in the card's accent; the letters come in across the whole of the closer and the last one
// lands on the stop, the handle comes up under it in the text face, and the whole block moves toward the viewer at an
// even rate until the stop. The lines and the handle stand inside the safe area, clear of the app's own header, caption
// and buttons.
import React from 'react';
import {alpha, fill, HANDLE, handleOn, land, measure, OPTICAL, OUT, px, safeOf, setLines, span, Words, wordsOf} from '../kit';
import type {CloserProps} from '../types';

/** The letters' tracking, em. */
const TRACK = -0.03;

const Closer: React.FC<CloserProps> = ({look, u}) => {
  const text = wordsOf(look.signoff.toUpperCase()).join(' ');
  const count = Math.max(1, text.replace(/ /g, '').length);
  // a letter lands 0.7 of (2.5 per + 0.02) after it starts, so the last one lands on the stop
  const per = (1 - 0.7 * 0.02) / (count - 1 + 0.7 * 2.5);
  const [sl, st, sr, sb] = safeOf(look);
  const handH = look.handle ? px(look, 48) + px(look, HANDLE) * 1.2 : 0;
  // each letter is set on its own, with no kerning between letters, so a line is measured letter by letter, as it is
  // drawn, and the widest fills the safe width at the stop, where the block stands at full scale; the lines and the
  // handle fit the safe height, and never take more than 0.6 of the frame's
  const wide = new Map([...new Set(text)].map((ch) => [ch, measure(ch, look.display, 1, 800, 0) + TRACK]));
  const lineW = (ln: string) => [...ln].reduce((sum, ch) => sum + (wide.get(ch) ?? 0), 0);
  const {lines, size} = setLines(text, 5, (ls) => Math.min((sr - sl) / Math.max(1e-3, ...ls.map(lineW)), Math.min(look.H * 0.6, sb - st - handH) / (ls.length * 0.92)));
  const hand = handleOn(look, look.colors.bg, look.colors.accent, 1);
  let n = 0;
  return (
    <div style={{...fill, background: alpha(look.colors.bg, span(u, 0, 0.2, OUT)), display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: `${st}px ${look.W - sr}px ${look.H - sb}px ${sl}px`, boxSizing: 'border-box'}}>
      <div style={{transform: `scale(${0.96 + 0.04 * span(u, 0, 1)})`, transformOrigin: '50% 50%'}}>
      {lines.map((ln, li) => (
        <div key={li} style={{display: 'flex', whiteSpace: 'pre', fontFamily: `'${look.display}'`, fontWeight: 800, fontSize: size, lineHeight: 0.92, color: look.colors.accent, letterSpacing: `${TRACK}em`, ...OPTICAL}}>
          {[...ln].map((ch, ci) => {
            if (ch === ' ') return <span key={ci} style={{display: 'inline-block'}}>{ch}</span>;
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
