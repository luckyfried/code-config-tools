// title-card: the last still dims under the card's matte and still reads through it, the film's title set across the
// measure in the display face's capitals, widely spaced and drifting slowly toward the viewer, the closing line under
// it in the text face's italic and the handle at the foot, and the letterbox bars closing on it at the stop. The title,
// the closing line and the handle stand as one block in the middle of the picture left open between the bars at the
// stop, the title set smaller where the block would otherwise reach a bar. Everything is timed by the closer's progress
// to the stop, so the push settles on the last moving frame.
import React from 'react';
import {alpha, balance, fill, fitTo, HANDLE, handleOn, inkOn, OUT, px, SINE, span, Words} from '../kit';
import type {CloserProps} from '../types';

/** Each letterbox bar's height as the closer opens and at the stop, a share of the frame. */
const OPEN = 0.12, SHUT = 0.32;

/** How far the matte dims the last still under the words: the picture still reads and the words stand clear of it. */
const MATTE = 0.6;

const Closer: React.FC<CloserProps> = ({look, u}) => {
  const title = (look.title || look.signoff).toUpperCase();
  const words = look.colors;
  const a = span(u, 0, 0.45, SINE);
  const bar = look.H * (OPEN + (SHUT - OPEN) * span(u, 0.86, 0.14, SINE));
  const side = px(look, 100), width = look.W - 2 * side;
  const lines = balance(title, title.length > 16 ? 2 : 1);
  const said = look.title ? balance(look.signoff, look.signoff.length > 26 ? 2 : 1) : [];
  const saidSize = said.length ? Math.min(px(look, 64), fitTo(said, look.text, width * 0.9)) : 0;
  const handH = look.handle ? px(look, HANDLE) * 1.12 : 0;
  // the block's height beside the title: the closing line and the handle with the space above each
  const rest = (said.length ? px(look, 40) + said.length * saidSize * 1.2 : 0) + (look.handle ? px(look, 50) + handH : 0);
  const room = look.H * (1 - 2 * SHUT) - 2 * px(look, 40);
  const size = Math.min(fitTo(lines, look.display, width, {tracking: 0.14, most: px(look, 210)}), (room - rest) / (lines.length * 1.05));
  const ink = inkOn(look.tone.matte, [words.paper, look.tone.light, words.ink]);
  const top = (look.H - (lines.length * size * 1.05 + rest)) / 2;
  const push = 1 + 0.035 * span(u, 0, 1, OUT);
  const saidTop = top + lines.length * size * 1.05 + px(look, 40);
  const handleTop = (said.length ? saidTop + said.length * saidSize * 1.2 : top + lines.length * size * 1.05) + px(look, 50);
  const hand = handleOn(look, look.tone.matte, ink, 0.85);
  const lift = `0 0 ${px(look, 28)}px ${alpha(look.tone.matte, 0.7)}`;
  return (
    <div style={fill}>
      <div style={{...fill, background: alpha(look.tone.matte, MATTE * a)}} />
      <div style={{...fill, transform: `scale(${push})`, transformOrigin: '50% 50%'}}>
        <Words text={lines.join('\n')} family={look.display} size={size} color={ink}
          style={{position: 'absolute', left: side - size * 0.07, right: side - size * 0.07, top, lineHeight: 1.05, textAlign: 'center', whiteSpace: 'pre', letterSpacing: '0.14em', textShadow: lift, opacity: span(u, 0.1, 0.4, SINE)}} />
        {said.length ? <Words text={said.join('\n')} family={look.text} size={saidSize} color={ink}
          style={{position: 'absolute', left: side, right: side, top: saidTop, lineHeight: 1.2, textAlign: 'center', fontStyle: 'italic', textShadow: lift, opacity: 0.88 * span(u, 0.35, 0.35, SINE)}} /> : null}
      </div>
      {look.handle ? <Words text={look.handle} family={look.text} size={px(look, HANDLE)} color={hand.color}
        style={{position: 'absolute', left: 0, right: 0, top: handleTop, textAlign: 'center', letterSpacing: '0.2em', textShadow: lift, opacity: hand.opacity * span(u, 0.5, 0.35, SINE)}} /> : null}
      <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: bar, background: look.tone.matte}} />
      <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: bar, background: look.tone.matte}} />
    </div>
  );
};

export default Closer;
