// Where each move, cut, and closer plays: a beat's move from the cut into it to the cut out of it (a frame-taking move
// from its beat's `early` seconds before that cut), a cut over its window centred on the moment of the cut, the closer
// from the closer's start to the stop and its slow push from the stop to the last frame; the camera's nudge and the
// travel pass's additions at a moment; and the one layer that draws them all over the picture, with the card's
// letterbox bars above everything.
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import type {Travel} from '../three/travel';
import {closerOf, cutOf, moveOf} from './index';
import {px, safeOf} from './kit';
import type {BeatOn, Look, MoveProps, Nudge} from './types';

/** The film's beats and the moments of the cuts between them: `cuts[i]` is when beat i begins (cuts[0] its start). */
export type Timeline = {beats: BeatOn[]; cuts: number[]};

/** The move beat `i` plays. A move the card marks `once` plays on the first beat the board gives it and on no later
 * one: a later beat takes the card's next move after it that fits the beat's form and is not itself a once move
 * already played, and no move when none does. Without the card's moves, the move the board gives. */
export const moveAt = (line: Timeline, look: Look, i: number): string | undefined => {
  const card = look.moves;
  if (!card?.length) return line.beats[i]?.move;
  const played = new Set<string>();
  let got: string | undefined;
  for (let k = 0; k <= i; k++) {
    const want = line.beats[k].move;
    got = want;
    const at = card.findIndex((m) => m.id === want);
    if (want && at >= 0 && card[at].once && played.has(want)) {
      got = undefined;
      for (let j = 1; j < card.length; j++) {
        const m = card[(at + j) % card.length];
        if (m.fits.includes(line.beats[k].form) && !(m.once && played.has(m.id))) {
          got = m.id;
          break;
        }
      }
    }
    if (got) played.add(got);
  }
  return got;
};

/** Beat `i`'s move props at `t`, its move the one it plays. */
const propsOf = (line: Timeline, look: Look, i: number, t: number): MoveProps => {
  const {beats, cuts} = line;
  const from = cuts[i], to = i + 1 < cuts.length ? cuts[i + 1] : beats[i].end;
  const local = t - from;
  const beat = {...beats[i], move: moveAt(line, look, i)};
  return {beat, look, u: Math.min(1, Math.max(0, local) / Math.max(0.05, to - from)), local, t, seed: i + 1};
};

/** The beat the film is on at `t`, and its move's props; none before the first beat's cut, so no move draws before
 * its beat begins. */
export const beatAt = (line: Timeline, look: Look, t: number): MoveProps | null => {
  for (let i = line.beats.length - 1; i >= 0; i--) {
    if (t >= line.cuts[i]) return propsOf(line, look, i, t);
  }
  return null;
};

/** The next beat's frame-taking move when it has begun over the tail of the beat the film is on: from the beat's
 * `early` seconds before its cut to the cut, its props with `local` counting up to 0 at the cut. */
export const earlyAt = (line: Timeline, look: Look, t: number): MoveProps | null => {
  const i = line.cuts.findIndex((c) => c > t);
  if (i < 0) return null;
  const lead = line.beats[i].early ?? 0;
  if (lead <= 0 || t < line.cuts[i] - (lead * look.fps) / look.pulse) return null;
  const p = propsOf(line, look, i, t);
  return moveOf(p.beat.move)?.early ? p : null;
};

/** The beats a cut into beat `i` plays over: its own length, never more than half the shorter of the two beats it
 * joins, so a short beat between two long cuts still stands clear of both for half its length. */
export const windowOf = (line: Timeline, i: number, beats: number) => {
  const len = (b: BeatOn) => b.end - b.at;
  return Math.min(beats, Math.min(len(line.beats[i - 1]), len(line.beats[i])) / 2);
};

/** The cut playing at `t`, if any: its beat, its name, and its progress through its window. */
export const cutAt = (line: Timeline, t: number) => {
  for (let i = 1; i < line.beats.length; i++) {
    const c = cutOf(line.beats[i].transition);
    if (!c || c.beats <= 0) continue;
    const w = windowOf(line, i, c.beats);
    if (w <= 0) continue;
    const u = (t - line.cuts[i] + w / 2) / w;
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

/** How much the closer grows a second once the picture has come to rest at the stop: a slow push about the safe area's
 * middle to the last frame, so the end card is never a still frame. */
export const DRIFT = 0.01;

/** The closer's scale at the film's own time `now` (beats, running on past the stop): 1 until `still`, then the drift. */
export const holdOf = (look: Look, still: number, now: number) => 1 + (DRIFT * Math.max(0, now - still) * look.pulse) / look.fps;

/** How far a glyph's ink stands past the box its words are set in, px on a frame 1080 wide: a letter's overshoot and
 * side bearing, a handle's descender. */
export const INK = 6;

/** The closer's slow push at the film's own time `now`, `left` frames before the film's last: the style that grows the
 * closer by `holdOf` about the safe area's middle, and the look the closer lays its words out in, whose safe area is the
 * safe area drawn in by `INK` and shrunk about that middle by the push the last frame reaches. The words' boxes grow to
 * `INK` inside the safe area's edges on the last frame, so their ink ends inside the safe area, and the closer's ground,
 * grown and never shrunk, still covers the frame. */
export const pushOf = (look: Look, still: number, now: number, left: number) => {
  const end = holdOf(look, still, now + Math.max(0, left) / look.pulse);
  const ink = px(look, INK);
  const [x0, y0, x1, y1] = safeOf(look);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
  const hw = (x1 - x0) / 2 - ink, hh = (y1 - y0) / 2 - ink;
  const safe = {left: cx - hw / end, top: cy - hh / end, right: look.W - cx - hw / end, bottom: look.H - cy - hh / end};
  const style: React.CSSProperties = {position: 'absolute', inset: 0, transform: `scale(${holdOf(look, still, now)})`, transformOrigin: `${cx}px ${cy}px`};
  return {look: {...look, safe}, style};
};

/** `pushOf` on the frame the composition is on, the frames left counted to the composition's last; with no `now` the
 * closer stands unpushed in the look's own safe area. A kit's own element on the end card takes the same style and lays
 * itself out in the same look, so it grows with the closer. */
export const usePush = (look: Look, still: number, now?: number) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  if (now === undefined) return {look, style: {position: 'absolute', inset: 0} as React.CSSProperties};
  return pushOf(look, still, now, durationInFrames - 1 - frame);
};

/** Every move, cut, and closer over the picture at `t`. The closer covers the frame from its start; `closer` names the
 * card's closer and when it runs. `children` is a kit's own element, drawn over the closer and under the letterbox
 * bars, so a kit's last element stands on the end card and takes the finish. `now` is the film's own time when the
 * picture holds `t` at the stop: from the stop on, the closer keeps its slow push to the last frame (`usePush`). */
export const MoveLayer: React.FC<{line: Timeline; look: Look; t: number; now?: number; closer?: {name: string; at: number; still: number}; bars: number; children?: React.ReactNode}> = ({line, look, t, now, closer, bars, children}) => {
  const p = beatAt(line, look, t);
  const m = p && moveOf(p.beat.move);
  const e = earlyAt(line, look, t);
  const n = e && moveOf(e.beat.move);
  const c = cutAt(line, t);
  const Shape = closer ? closerOf(closer.name) : undefined;
  const closing = Shape && closer && t >= closer.at;
  const bar = bars * look.H;
  const push = usePush(look, closer?.still ?? 0, now);
  return (
    <>
      {m?.Overlay && p && !(closing && p.beat.form === 'closer') ? <m.Overlay {...p} /> : null}
      {n?.Overlay && e ? <n.Overlay {...e} /> : null}
      {c?.cut.Overlay ? <c.cut.Overlay into={c.into} look={look} u={c.u} t={t} /> : null}
      {closing && closer && Shape ? (
        <div style={push.style}>
          <Shape look={push.look} local={t - closer.at} u={Math.min(1, (t - closer.at) / Math.max(0.05, closer.still - closer.at))} />
        </div>
      ) : null}
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
