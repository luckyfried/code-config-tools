// marquee: words run across two bands, one of the card's accent and one of its first ink, again and again, faster than
// the camera: the beat's own words, or on a beat that has none of its own (a photo beat, whose line the card sets) the
// film's title. Each band is one run of the words and a bullet in its gap, laid end to end, so the band repeats with no
// seam; the bands keep clear of where the beat's label and line stand.
import React from 'react';
import {fill, measure, px} from '../kit';
import type {BeatOn, Look, Move, MoveProps} from '../types';

const SPEED = 260;

/** The tops of the two bands, `band` px tall: near the head and near the foot of the frame, each moved off the beat's
 * label and line to the nearer side that keeps it in the frame. */
const bandsOf = (look: Look, beat: BeatOn, band: number): number[] => {
  const gap = px(look, 24);
  const clear = (y: number) => {
    if (!beat.type) return y;
    const [, t0, , t1] = beat.type;
    if (y + band <= t0 - gap || y >= t1 + gap) return y;
    const up = t0 - gap - band, down = t1 + gap;
    const fits = [up, down].filter((v) => v >= 0 && v + band <= look.H);
    return fits.length ? fits.reduce((a, b) => (Math.abs(b - y) < Math.abs(a - y) ? b : a)) : y;
  };
  return [clear(look.H * 0.1), clear(look.H * 0.74)];
};

const Overlay: React.FC<MoveProps> = ({look, beat, local}) => {
  const text = (beat.words || beat.label || look.title).toUpperCase();
  if (!text) return null;
  const band = px(look, 200);
  const size = band * 0.78;
  const space = size * 0.9;
  const unit = measure(text, look.text, size) + space;
  const count = Math.ceil(look.W / unit) + 2;
  return (
    <div style={fill}>
      {bandsOf(look, beat, band).map((y, i) => {
        const run = SPEED * px(look, 1) * local;
        const shift = (((i ? -run : run) % unit) + unit) % unit;
        return (
          <div key={i} style={{position: 'absolute', left: 0, right: 0, top: y, height: band, background: i ? look.colors.bg : look.colors.accent, overflow: 'hidden'}}>
            {Array.from({length: count}, (_, k) => (
              <div key={k} style={{position: 'absolute', top: band * 0.08, left: (k - 1) * unit + shift, width: unit, display: 'flex', whiteSpace: 'pre',
                fontFamily: `'${look.text}'`, fontSize: size, lineHeight: 1.12, color: i ? look.colors.accent : look.colors.bg}}>
                <span>{text}</span>
                <span style={{width: space, textAlign: 'center'}}>•</span>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
};

export default {Overlay} satisfies Move;
