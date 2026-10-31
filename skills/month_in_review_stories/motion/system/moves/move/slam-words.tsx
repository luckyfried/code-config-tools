// slam-words: the beat's words land one at a time, each dropping from three times its size out of a blur onto its
// place in the line, and every landing hits: the colors split for an instant, the frame shakes and settles, and a flash
// of the card's light shows for a sixth of a second. The words are set as large as the longest line allows, in the
// upper two thirds of the frame, about two words a line, so a short word never stands alone. On a photo beat they land
// over the photograph dimmed into the card's ground, on a clip beat over the clip dimmed the same way, and the line holds
// while the camera holds on the beat, leaving over the first of the pull back; on a words beat they hold to the end of
// the beat.
import React from 'react';
import {alpha, clamp01, heldOf, inkOn, measure, OPTICAL, PICTURED, px, setLines, wordsOf} from '../kit';
import {Face, landingOf} from '../arrival';
import {secondsOf, shake} from '../spring';
import type {BeatOn, Move, MoveProps} from '../types';

/** The beats after the beat's start each word lands on, every one on a quarter of a beat so the music's grid and the
 * sound's impacts fall with it: the first a quarter in, then one a beat, closer together (to the nearest quarter, never
 * under one) when the words would take more than about the first half of the beat. The sound pass lands an impact on each. */
export const landsOf = (beat: BeatOn, n: number) => {
  const until = beat.held ? beat.held[1] : beat.end;
  const every = Math.max(0.25, Math.round(4 * Math.min(1, (0.55 * Math.max(0.5, until - beat.at - 0.25)) / Math.max(1, n))) / 4);
  return Array.from({length: n}, (_, k) => beat.at + 0.25 + k * every);
};

/** Seconds a word takes to fall from three times its size onto its place. */
const FALL = 0.14;

/** The space between two words as they stand in the line, em. */
const GAP = 0.26;

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, t, seed} = p;
  const over = PICTURED.has(beat.form);
  const text = beat.words || beat.say || beat.label;
  const {box: [x, y, w, h], src, place} = landingOf(p);
  const words = wordsOf(text);
  if (!words.length) return null;
  const lands = landsOf(beat, words.length);
  const shows = over ? heldOf(beat, t) : 1;
  if (shows <= 0) return null;
  const field = over ? look.tone.ground : look.colors.bg;
  const ink = inkOn(field, [look.colors.ink, look.colors.accent, look.colors.paper, look.tone.pen]);
  // the largest words inside the measure and the upper two thirds, each line measured as it is drawn: its words side by
  // side, GAP apart
  const m = look.grid.m || px(look, 72);
  const width = (look.W - 2 * m) * 0.96;
  const room = look.H * 0.62 - m;
  const wide = new Map(words.map((wd) => [wd, measure(wd, look.display, 1, 800, -0.02)]));
  const em = (ln: string) => wordsOf(ln).reduce((a, wd) => a + (wide.get(wd) ?? 0), 0) + GAP * (wordsOf(ln).length - 1);
  const {lines, size} = setLines(text, 5, (ls) => Math.min(width / Math.max(...ls.map(em)), px(look, 300), room / (ls.length * 1.04)));
  const top = Math.max(m, Math.min(look.H * 0.36 - (lines.length * size * 1.04) / 2, look.H * 0.66 - lines.length * size * 1.04));
  // the latest landing drives the hit: its shake, its split and its flash
  const ages = lands.map((l) => secondsOf(look, t - l));
  const hit = ages.reduce((a, b, k) => (b >= 0 ? k : a), -1);
  const age = hit >= 0 ? ages[hit] : -1;
  const sh = hit >= 0 ? shake(age, seed * 7 + hit, px(look, 20)) : {x: 0, y: 0, r: 0};
  const split = hit >= 0 ? px(look, 14) * Math.max(0, 1 - age / 0.12) : 0;
  const a1 = look.colors.accent !== field ? look.colors.accent : look.tone.light;
  const a2 = look.colors.accent2 && look.colors.accent2 !== field && look.colors.accent2 !== a1 ? look.colors.accent2 : look.tone.light;
  let k = -1;
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', opacity: shows}}>
      <div style={{position: 'absolute', inset: -px(look, 40), transform: `translate(${sh.x}px, ${sh.y}px) rotate(${sh.r}deg)`}}>
        <div style={{position: 'absolute', inset: px(look, 40), background: beat.form === 'clip' ? alpha(field, 0.74) : field}} />
        {beat.form === 'photo' && src ? (
          <div style={{position: 'absolute', left: x + px(look, 40), top: y + px(look, 40), width: w, height: h}}>
            <Face src={src} w={w} h={h} place={place}>
              <div style={{position: 'absolute', inset: 0, background: alpha(field, 0.74)}} />
            </Face>
          </div>
        ) : null}
        <div style={{position: 'absolute', left: m + px(look, 40), top: top + px(look, 40), width, fontFamily: `'${look.display}'`, fontWeight: 800,
          fontSize: size, lineHeight: 1.04, letterSpacing: '-0.02em', color: ink, ...OPTICAL}}>
          {lines.map((ln, li) => (
            <div key={li} style={{whiteSpace: 'nowrap'}}>
              {wordsOf(ln).map((wd, wi) => {
                k += 1;
                const a = ages[k];
                const fall = clamp01((a + FALL) / FALL);
                const z = 3 - 2 * fall * fall;
                const sp = k === hit ? split : 0;
                return (
                  <span key={wi} style={{display: 'inline-block', marginRight: wi < wordsOf(ln).length - 1 ? `${GAP}em` : 0,
                    opacity: a < -FALL ? 0 : Math.min(1, fall * 2.5), transform: `scale(${z})`, transformOrigin: '50% 60%',
                    filter: fall < 1 ? `blur(${(px(look, 16) * (1 - fall)).toFixed(2)}px)` : undefined,
                    textShadow: sp > 0.5 ? `${sp}px 0 ${a1}, ${-sp}px 0 ${a2}` : undefined}}>{wd}</span>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      {age >= 0 && age < 0.16 ? <div style={{position: 'absolute', inset: 0, background: alpha(look.tone.light, 0.2)}} /> : null}
    </div>
  );
};

export default {Overlay} satisfies Move;
