// word-per-beat-slam: a flat field of the card's first ink and the beat's words on it one at a time, one a musical
// beat, each slamming down from oversize onto its place in the second ink. A word is set at the size it fills the
// measure at, but never more than RANGE times the size the beat's longest word fills it at, so a short word after a long
// one lands large without towering over it. A word starts from as far over its size as the frame holds, up to the full
// slam, so no word ever leaves the frame.
import React from 'react';
import {fill, fitTo, land, measure, px, Words, wordsOf} from '../kit';
import type {Move, MoveProps} from '../types';

/** How far over its size a word starts its slam, at most. */
const SLAM = 1.6;
const WEIGHT = 800, TRACKING = -0.02;
/** How much larger than the beat's longest word a shorter word is set, at most. */
const RANGE = 1.6;

const Overlay: React.FC<MoveProps> = ({look, beat, local}) => {
  const words = wordsOf(beat.words || beat.label);
  if (!words.length) return null;
  const i = Math.min(words.length - 1, Math.floor(local));
  const w = words[i];
  const k = land(local - i);
  const sizeOf = (ws: string[], most: number) => fitTo(ws, look.display, look.W - px(look, 120), {weight: WEIGHT, tracking: TRACKING, most});
  const size = sizeOf([w], Math.min(px(look, 330), RANGE * sizeOf(words, Infinity)));
  const start = Math.max(1, Math.min(SLAM, (look.W - px(look, 40)) / measure(w, look.display, size, WEIGHT, TRACKING)));
  return (
    <div style={{...fill, background: look.colors.bg, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <Words text={w} family={look.display} size={size} color={look.colors.accent}
        style={{transform: `scale(${start - (start - 1) * k})`, whiteSpace: 'pre', letterSpacing: `${TRACKING}em`, fontWeight: WEIGHT}} />
    </div>
  );
};

export default {Overlay} satisfies Move;
