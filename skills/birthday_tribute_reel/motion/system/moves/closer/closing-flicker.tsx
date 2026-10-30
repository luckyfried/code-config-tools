// closing-flicker: the person's closing line on the dark of a projector screen, set across the measure in the display
// face, in the lamp's light, flickering with the lamp and weaving in the gate as the roll runs out, the screen's edge
// falling off into the card's matte, the handle under the line in the text face, the weave easing out as the lamp
// steadies on the stop. Nothing is set that the person did not write.
import React from 'react';
import {alpha, balance, fill, fitTo, HANDLE, handleOn, hash, px, smoothNoise, span, Words} from '../kit';
import type {CloserProps} from '../types';

const Closer: React.FC<CloserProps> = ({look, local, u}) => {
  const frame = Math.floor(local * look.pulse);
  const calm = 1 - span(u, 0.6, 0.4);
  const lamp = 1 - calm * 0.2 * (1 - hash(frame * 3.1) * (hash(frame) > 0.6 ? 1 : 0.4));
  const dx = calm * px(look, 6) * smoothNoise(local * 8, 2), dy = calm * px(look, 9) * smoothNoise(local * 6, 5);
  const a = span(u, 0, 0.35);
  const side = px(look, 110), width = look.W - 2 * side;
  const n = look.signoff.length > 30 ? 3 : look.signoff.length > 12 ? 2 : 1;
  const lines = balance(look.signoff, n);
  const size = Math.min(fitTo(lines, look.display, width, {most: px(look, 220)}), (look.H * 0.5) / (lines.length * 1.05));
  const top = look.H * 0.44 - (lines.length * size * 1.05) / 2;
  const hand = handleOn(look, look.colors.bg, look.tone.light, 0.8);
  return (
    <div style={{...fill, background: alpha(look.colors.bg, a)}}>
      <div style={{...fill, background: `radial-gradient(ellipse 80% 46% at 50% 44%, ${alpha(look.tone.light, 0.2 * lamp)}, transparent 75%)`}} />
      <Words text={lines.join('\n')} family={look.display} size={size} color={look.tone.light}
        style={{position: 'absolute', left: side, right: side, top, lineHeight: 1.05, textAlign: 'center', whiteSpace: 'pre', opacity: lamp * span(u, 0.1, 0.4),
          transform: `translate(${dx}px, ${dy}px)`, textShadow: `0 0 ${px(look, 22)}px ${alpha(look.colors.accent, 0.4)}`}} />
      {look.handle ? <Words text={look.handle} family={look.text} size={px(look, HANDLE)} color={hand.color}
        style={{position: 'absolute', left: side, right: side, top: top + lines.length * size * 1.05 + px(look, 56), textAlign: 'center', letterSpacing: '0.16em',
          opacity: hand.opacity * lamp * span(u, 0.45, 0.35), transform: `translate(${dx}px, ${dy}px)`}} /> : null}
      <div style={{...fill, borderRadius: px(look, 70), boxShadow: `inset 0 0 ${px(look, 160)}px ${px(look, 50)}px ${alpha(look.tone.matte, 0.9)}`}} />
    </div>
  );
};

export default Closer;
