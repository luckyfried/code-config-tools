// counter: the beat's number counts up from nothing, fast and then slowing onto its value, and on the stop four rings
// open out from it one after another in the card's accents while a burst of sparks flies off it and falls. The rest of
// the beat's words stand under the number in the text face. On a photo beat the count plays over the photograph dimmed
// into the card's ground, then the frame goes back to the picture; on a words beat it holds to the end of the beat.
import React from 'react';
import {alpha, clamp01, fitTo, hash, inkOn, px, SINE, wordsOf} from '../kit';
import {Face, landingOf} from '../arrival';
import {secondsOf, spring} from '../spring';
import type {Move, MoveProps} from '../types';

const SMALL = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'];

/** The first number in `text`, written in figures or as a word up to twelve, with the words around it; the beat's place
 * in the film when the text has none. */
const numberOf = (text: string, seed: number) => {
  const ws = wordsOf(text);
  for (let i = 0; i < ws.length; i++) {
    const bare = ws[i].toLowerCase().replace(/[^a-z0-9.,]/g, '');
    const fig = /^\d[\d,]*(\.\d+)?$/.test(bare) ? Number(bare.replace(/,/g, '')) : SMALL.indexOf(bare);
    if (fig >= 0 && Number.isFinite(fig)) return {value: fig, rest: [...ws.slice(0, i), ...ws.slice(i + 1)].join(' '), grouped: bare.includes(',')};
  }
  return {value: seed, rest: text, grouped: false};
};

/** Seconds the count takes, and the seconds a ring and a spark live after the stop. */
const COUNT = 0.85, RING = 0.7, SPARK = 0.8;

const Overlay: React.FC<MoveProps> = (p) => {
  const {look, beat, seed} = p;
  const photoBeat = beat.form === 'photo';
  const {box: [x, y, w, h], src, place} = landingOf(p);
  const {value, rest, grouped} = numberOf(beat.words || beat.say || beat.label, seed);
  const s = secondsOf(look, p.local);
  const until = secondsOf(look, (beat.held ? beat.held[1] : beat.end) - (p.t - p.local));
  const count = Math.min(COUNT, until * 0.45);
  // a photo beat hands the frame back after the count has held a moment: the number goes first, then the dimmed
  // photograph clears onto the picture, so the number never crosses the words the photo form sets
  const hand = s - Math.min(count + 0.9, until - 0.5);
  const shows = photoBeat ? 1 - SINE(clamp01((hand - 0.14) / 0.3)) : 1;
  const inked = photoBeat ? 1 - SINE(clamp01(hand / 0.18)) : 1;
  if (shows <= 0) return null;
  const k = clamp01(s / count);
  // fast and then slowing: the value follows an exponential ease that lands exactly on it
  const shown = k >= 1 ? value : Math.floor(value * (1 - Math.pow(2, -10 * k)) / (1 - Math.pow(2, -10)));
  const digits = value % 1 ? shown.toFixed(1) : grouped ? shown.toLocaleString('en-US') : String(shown);
  const final = value % 1 ? value.toFixed(1) : grouped ? value.toLocaleString('en-US') : String(value);
  const field = photoBeat ? look.tone.ground : look.colors.bg;
  const ink = inkOn(field, [look.colors.ink, look.colors.accent, look.colors.paper, look.tone.pen]);
  const m = look.grid.m || px(look, 72);
  // the size the final value is set at decides the number's size, so the count never grows wider than its stop
  const size = Math.min(fitTo([final], look.display, look.W - 2 * m, {weight: 800, most: px(look, 420)}), look.H * 0.24);
  const cy = look.H * 0.34;
  const restSize = rest ? fitTo([rest], look.text, look.W - 2 * m, {weight: 600, most: px(look, 64)}) : 0;
  const after = s - count;
  // the stop punches the number up and it springs back to its size
  const pop = after >= 0 ? 1 + 0.14 * (1 - spring(after, 420, 18)) : 1;
  const a1 = look.colors.accent !== field ? look.colors.accent : look.tone.light;
  const a2 = look.colors.accent2 && look.colors.accent2 !== field ? look.colors.accent2 : look.tone.light;
  const rings = after >= 0 ? [0, 1, 2, 3].map((i) => {
    const age = after - i * 0.07;
    if (age < 0 || age > RING) return null;
    const u = age / RING;
    const r = size * 0.45 + look.W * 0.55 * (1 - Math.pow(1 - u, 3));
    return <div key={i} style={{position: 'absolute', left: look.W / 2 - r, top: cy - r, width: 2 * r, height: 2 * r, borderRadius: '50%',
      border: `${px(look, 10) * (1 - u) + 1}px solid ${i % 2 ? a2 : a1}`, opacity: 1 - u}} />;
  }) : null;
  const sparks = after >= 0 && after < SPARK ? Array.from({length: 30}, (_, i) => {
    const ang = Math.PI * 2 * (i / 30) + hash(seed * 11 + i) * 0.3;
    const v = look.W * (0.35 + 0.35 * Math.abs(hash(seed * 5 + i * 3)));
    const sx = look.W / 2 + Math.cos(ang) * v * after;
    const sy = cy + Math.sin(ang) * v * after + 0.5 * look.H * 0.9 * after * after;
    const sz = px(look, 7 + 6 * Math.abs(hash(i * 17 + seed)));
    const color = [a1, a2, look.tone.light][i % 3];
    // a spark that would fall into the frame's bottom third is gone before it gets there
    if (sy > look.H * 0.66) return null;
    return <div key={i} style={{position: 'absolute', left: sx - sz / 2, top: sy - sz / 2, width: sz, height: sz, borderRadius: '50%',
      background: color, opacity: 1 - after / SPARK}} />;
  }) : null;
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', opacity: shows, background: field}}>
      {photoBeat && src ? (
        <div style={{position: 'absolute', left: x, top: y, width: w, height: h}}>
          <Face src={src} w={w} h={h} place={place}>
            <div style={{position: 'absolute', inset: 0, background: alpha(field, 0.76)}} />
          </Face>
        </div>
      ) : null}
      {rings}
      <div style={{position: 'absolute', left: 0, right: 0, top: cy - size * 0.56, textAlign: 'center', fontFamily: `'${look.display}'`, fontWeight: 800,
        fontSize: size, lineHeight: 1.12, color: ink, fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.02em', transform: `scale(${pop})`, opacity: inked}}>{digits}</div>
      {rest ? <div style={{position: 'absolute', left: m, right: m, top: cy + size * 0.62, textAlign: 'center', fontFamily: `'${look.text}'`, fontWeight: 600,
        fontSize: restSize, lineHeight: 1.2, color: ink, whiteSpace: 'nowrap', opacity: inked * SINE(clamp01((s - count * 0.6) / 0.3))}}>{rest}</div> : null}
      {sparks}
    </div>
  );
};

export default {Overlay} satisfies Move;
