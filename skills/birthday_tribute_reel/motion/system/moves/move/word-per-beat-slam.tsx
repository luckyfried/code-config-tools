// word-per-beat-slam: a flat field of the card's first ink and the beat's words on it one at a time, one a musical
// beat and never more, each slamming down from oversize onto its place in the second ink. A beat with more words than
// musical beats sets the words that have no beat of their own beside the word before, so every word lands and every
// landing is on its own beat of the grid (the sound pass lays one impact on each). A word is set at the size it fills
// the measure at, but never more than RANGE times the size the beat's longest word fills it at, so a short word after a
// long one lands large without towering over it. The measure is the profile's safe area, and each word comes to rest on
// the safe area's middle, so a landed word sits where the profile's own buttons never cover it. A word starts from as
// far over its size as the frame holds, up to the full slam, so no word ever leaves the frame. On a beat whose form has
// a picture of its own (a title, a photograph, a clip), the field and the last word leave a musical beat after it
// lands, handing the frame back to the form; on any other form they hold to the end of the beat.
import React from 'react';
import {fill, fitTo, land, measure, PICTURED, px, safeOf, span, Words, wordsOf} from '../kit';
import type {BeatOn, Move, MoveProps} from '../types';

/** How far over its size a word starts its slam, at most. */
const SLAM = 1.6;
const WEIGHT = 800, TRACKING = -0.02;
/** How much larger than the beat's longest word a shorter word is set, at most. */
const RANGE = 1.6;

/** What lands on each musical beat of the beat: one word a beat while the beat has a beat for every word, else the
 * words in as many runs as the beat has musical beats, each run starting a beat. */
export const slamsOf = (beat: Pick<BeatOn, 'at' | 'end' | 'words' | 'label'>) => {
  const words = wordsOf(beat.words || beat.label);
  const n = Math.min(words.length, Math.max(1, Math.ceil(beat.end - beat.at - 1e-6)));
  return Array.from({length: words.length ? n : 0}, (_, i) => words.slice(Math.floor((i * words.length) / n), Math.floor(((i + 1) * words.length) / n)).join(' '));
};

/** How long the field takes to leave, in musical beats. */
const LEAVE = 0.35;

/** When, in musical beats into the beat, the field starts to leave: a beat after the last word lands, on a form with a
 * picture of its own and room left in the beat to leave, else never (null). */
export const leavesAt = (beat: Pick<BeatOn, 'at' | 'end' | 'words' | 'label' | 'form'>) => {
  const at = slamsOf(beat).length + 1;
  return (PICTURED.has(beat.form) || beat.form === 'title') && at + LEAVE <= beat.end - beat.at ? at : null;
};

const Overlay: React.FC<MoveProps> = ({look, beat, local}) => {
  const slams = slamsOf(beat);
  if (!slams.length) return null;
  const leaves = leavesAt(beat);
  const shown = leaves === null ? 1 : 1 - span(local, leaves, leaves + LEAVE);
  if (shown <= 0) return null;
  const i = Math.min(slams.length - 1, Math.floor(local));
  const w = slams[i];
  const k = land(local - i);
  const [sx0, , sx1] = safeOf(look);
  const sizeOf = (ws: string[], most: number) => fitTo(ws, look.display, sx1 - sx0, {weight: WEIGHT, tracking: TRACKING, most});
  const size = sizeOf([w], Math.min(px(look, 330), RANGE * sizeOf(slams, Infinity)));
  const start = Math.max(1, Math.min(SLAM, (look.W - px(look, 40)) / measure(w, look.display, size, WEIGHT, TRACKING)));
  return (
    <div style={{...fill, opacity: shown, background: look.colors.bg, display: 'flex', alignItems: 'center', justifyContent: 'center',
      paddingLeft: sx0, paddingRight: look.W - sx1}}>
      <Words text={w} family={look.display} size={size} color={look.colors.accent}
        style={{transform: `scale(${start - (start - 1) * k})`, whiteSpace: 'pre', letterSpacing: `${TRACKING}em`, fontWeight: WEIGHT}} />
    </div>
  );
};

export default {Overlay} satisfies Move;
