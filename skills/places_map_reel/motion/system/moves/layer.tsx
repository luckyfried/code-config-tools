// Where each move, cut, and closer plays: a beat's move from the cut into it to the cut out of it, a cut over its window
// centred on the moment of the cut, the closer from the closer's start to the stop; the camera's nudge and the travel
// pass's additions at a moment; and the one layer that draws them all over the picture, with the card's letterbox bars
// above everything.
import React from 'react';
import type {Travel} from '../three/travel';
import {closerOf, cutOf, moveOf} from './index';
import type {BeatOn, Look, MoveProps, Nudge} from './types';

/** The film's beats and the moments of the cuts between them: `cuts[i]` is when beat i begins (cuts[0] its start). */
export type Timeline = {beats: BeatOn[]; cuts: number[]};

/** The beat the film is on at `t`, and its move's props. */
export const beatAt = (line: Timeline, look: Look, t: number): MoveProps | null => {
  const {beats, cuts} = line;
  for (let i = beats.length - 1; i >= 0; i--) {
    if (t >= cuts[i] || i === 0) {
      const from = cuts[i], to = i + 1 < cuts.length ? cuts[i + 1] : beats[i].end;
      const local = Math.max(0, t - from);
      return {beat: beats[i], look, u: Math.min(1, local / Math.max(0.05, to - from)), local, t, seed: i + 1};
    }
  }
  return null;
};

/** The cut playing at `t`, if any: its beat, its name, and its progress through its window. */
export const cutAt = (line: Timeline, t: number) => {
  for (let i = 1; i < line.beats.length; i++) {
    const c = cutOf(line.beats[i].transition);
    if (!c || c.beats <= 0) continue;
    const u = (t - line.cuts[i] + c.beats / 2) / c.beats;
    if (u >= 0 && u <= 1) return {into: line.beats[i], cut: c, u};
  }
  return null;
};

/** The forms whose words the board lays out against a camera that holds the card whole and still: on them a move draws
 * over the picture and never turns the camera, so every word stands where the board checked it. */
const HELD = new Set(['words', 'clip', 'screen']);

/** How the beat's move turns the camera at `t`. */
export const nudgeAt = (line: Timeline, look: Look, t: number): Nudge => {
  const p = beatAt(line, look, t);
  const m = p && !HELD.has(p.beat.form) ? moveOf(p.beat.move) : undefined;
  return p && m?.nudge ? m.nudge(p) : {};
};

/** What the beat's move and the cut playing add to the travel pass at `t`. */
export const fxAt = (line: Timeline, look: Look, t: number): Partial<Travel> => {
  const p = beatAt(line, look, t);
  const m = p && moveOf(p.beat.move);
  const c = cutAt(line, t);
  return {...(p && m?.fx ? m.fx(p) : {}), ...(c?.cut.fx ? c.cut.fx({into: c.into, look, u: c.u, t}) : {})};
};

/** Every move, cut, and closer over the picture at `t`. The closer covers the frame from its start; `closer` names the
 * card's closer and when it runs. `children` is a kit's own element, drawn over the closer and under the letterbox
 * bars, so a kit's last element stands on the end card and takes the finish. */
export const MoveLayer: React.FC<{line: Timeline; look: Look; t: number; closer?: {name: string; at: number; still: number}; bars: number; children?: React.ReactNode}> = ({line, look, t, closer, bars, children}) => {
  const p = beatAt(line, look, t);
  const m = p && moveOf(p.beat.move);
  const c = cutAt(line, t);
  const Shape = closer ? closerOf(closer.name) : undefined;
  const closing = Shape && closer && t >= closer.at;
  const bar = bars * look.H;
  return (
    <>
      {m?.Overlay && p && !(closing && p.beat.form === 'closer') ? <m.Overlay {...p} /> : null}
      {c?.cut.Overlay ? <c.cut.Overlay into={c.into} look={look} u={c.u} t={t} /> : null}
      {closing && closer && Shape ? <Shape look={look} local={t - closer.at} u={Math.min(1, (t - closer.at) / Math.max(0.05, closer.still - closer.at))} /> : null}
      {children}
      {bar > 0 ? (
        <>
          <div style={{position: 'absolute', left: 0, right: 0, top: 0, height: bar, background: look.tone.matte}} />
          <div style={{position: 'absolute', left: 0, right: 0, bottom: 0, height: bar, background: look.tone.matte}} />
        </>
      ) : null}
    </>
  );
};
