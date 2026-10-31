// What the spectacle moves share: when a beat's spectacle plays and where it lands, the photograph it lands, and that
// photograph drawn the way the camera holds it, so the move can hand the frame back to the picture without a jump.
import React, {type CSSProperties} from 'react';
import {Img} from 'remotion';
import {clamp01, pictureOf, SINE} from './kit';
import {secondsOf} from './spring';
import type {MoveProps} from './types';

type Box = [number, number, number, number];

/** A beat's spectacle in seconds since the cut into it: `s` now, `land` when it lands on the photograph, `out` when the
 * move has handed the frame back, `shows` how much of the move is over the picture (1 until it lands, 0 from `out`),
 * and `room` the seconds from the cut to the pull back to the wall (or the beat's end). The spectacle takes `want`
 * seconds when the beat has room, and lands within the first part of a short beat, so every move has settled and gone
 * before the pull. */
export const arrivalOf = (p: MoveProps, want = 1) => {
  const {beat, look, t, local} = p;
  const start = t - local;
  const room = Math.max(0.3, secondsOf(look, (beat.held ? beat.held[1] : beat.end) - start));
  const s = secondsOf(look, local);
  const land = Math.min(want, room * 0.55);
  const out = Math.min(land + 0.38, room - 0.12);
  const shows = 1 - SINE(clamp01((s - land) / Math.max(0.05, out - land)));
  return {s, land, out, shows, room};
};

/** The photograph a beat lands: its own, else the film's ground photograph. Its box on the frame, and where the
 * photograph lies relative to that box (absent: it covers the box). */
export const landingOf = (p: MoveProps) => {
  const box = pictureOf(p.look, p.beat) as Box;
  const src = p.beat.photo ?? p.look.photo;
  const place = p.beat.place ? ([p.beat.place[0] - box[0], p.beat.place[1] - box[1], p.beat.place[2], p.beat.place[3]] as Box) : undefined;
  return {box, src, place};
};

/** Every photograph the film has, the beat's own first; just the beat's own when the film lists none. */
export const photosOf = (p: MoveProps) => {
  const own = p.beat.photo ?? p.look.photo;
  const all = p.look.photos?.length ? p.look.photos : own ? [own] : [];
  return own ? [own, ...all.filter((s) => s !== own)] : all;
};

/** A photograph filling a `w` x `h` face: laid at `place` (px from the face's corner) when given, else covering it.
 * The frame waits for the photograph to decode, so no frame shows the face without it. */
export const Face: React.FC<{src?: string; w: number; h: number; place?: Box; style?: CSSProperties; children?: React.ReactNode}> = ({src, w, h, place, style, children}) => (
  <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, overflow: 'hidden', ...style}}>
    {src ? (place
      ? <Img src={src} style={{position: 'absolute', left: place[0], top: place[1], width: place[2], height: place[3]}} />
      : <Img src={src} style={{position: 'absolute', left: 0, top: 0, width: '100%', height: '100%', objectFit: 'cover'}} />) : null}
    {children}
  </div>
);
