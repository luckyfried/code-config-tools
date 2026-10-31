// book-cover: the scrapbook closes on its cover: the page comes up over the last spread and a cloth cover in whichever
// of the card's accents stands furthest from the page swings in over it, centred on the page, with a ruled inset. The
// film's title is written large on the lines balance sets in the display face, the closing line under it in the text
// face and the handle under that, the three set as one column centred in the inset, so the cover reads as one block
// however many lines the title takes; the cover lands by half way to the stop and settles there.
import React from 'react';
import {alpha, balance, fill, fitTo, HANDLE, handleOn, inkOn, land, px, span, Words} from '../kit';
import type {CloserProps} from '../types';

/** The cover's share of the page height, centred on it. */
const COVER = 0.72;

const Closer: React.FC<CloserProps> = ({look, u}) => {
  const page = look.tone.ground;
  const cover = inkOn(page, [look.colors.accent, look.colors.accent2]);
  const ink = inkOn(cover, [look.colors.paper, look.colors.ink, page]);
  const k = land(0.3 + 0.7 * u);
  const title = look.title || look.signoff;
  const side = px(look, 60), inset = px(look, 60);
  const inner = look.W - 2 * side - 4 * inset;
  const room = look.H * COVER - 4 * inset;
  const said = look.title ? balance(look.signoff, look.signoff.length > 22 ? 2 : 1) : [];
  const saidSize = said.length ? Math.min(px(look, 62), fitTo(said, look.text, inner)) : 0;
  const gap = px(look, 50);
  const rest = (said.length ? gap + said.length * saidSize * 1.2 : 0) + (look.handle ? gap + px(look, HANDLE) * 1.2 : 0);
  const lines = balance(title, title.length > 12 ? 2 : 1);
  const size = Math.min(fitTo(lines, look.display, inner, {most: px(look, 420)}), (room - rest) / lines.length);
  const hand = handleOn(look, cover, ink, 1);
  const top = (look.H * (1 - COVER)) / 2;
  return (
    <div style={fill}>
      <div style={{...fill, background: page, opacity: span(u, 0, 0.25)}} />
      <div style={{position: 'absolute', left: side, right: side, top, bottom: top, background: cover,
        borderRadius: px(look, 18), boxShadow: `0 ${px(look, 20)}px ${px(look, 50)}px ${alpha(look.tone.matte, 0.3)}`, transform: `translateX(${(1 - k) * look.W * 0.8}px) rotate(${(1 - k) * 8 - 1}deg)`}}>
        <div style={{position: 'absolute', left: inset, right: inset, top: inset, bottom: inset, border: `${px(look, 5)}px solid ${ink}`, borderRadius: px(look, 8), opacity: 0.8}} />
        <div style={{position: 'absolute', left: inset * 2, right: inset * 2, top: inset * 2, bottom: inset * 2, display: 'flex', flexDirection: 'column',
          justifyContent: 'center', alignItems: 'center', textAlign: 'center'}}>
          <Words text={lines.join('\n')} family={look.display} size={size} color={ink} style={{lineHeight: 1, whiteSpace: 'pre'}} />
          {said.length ? <Words text={said.join('\n')} family={look.text} size={saidSize} color={ink}
            style={{marginTop: gap, lineHeight: 1.2, whiteSpace: 'pre', opacity: span(u, 0.4, 0.35)}} /> : null}
          {look.handle ? <Words text={look.handle} family={look.text} size={px(look, HANDLE)} color={hand.color}
            style={{marginTop: gap, lineHeight: 1.2, letterSpacing: '0.08em', opacity: hand.opacity * span(u, 0.55, 0.35)}} /> : null}
        </div>
      </div>
    </div>
  );
};

export default Closer;
