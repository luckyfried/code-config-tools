import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {BeatProvider, FontGate, framesOf, SystemProvider, useMotion} from '../system/system';
import {Finish} from '../system/texture';
import {Move} from '../system/transitions';
import type {Beat, FilmProps, Layer} from '../system/types';
import {DriveFilm} from './drive/DriveFilm';
import {Bars, Cut, Scale, Slice, Tag, Tape, Tile, Tub, Twine, Words, YearRule} from './nine';

/** The best nine's layer kinds: the cut and its bars; the year's rule, its twine, tiles and tags; the proofing tubs, their scale and tape; words set where the composition puts them. */
const KINDS: Record<string, React.FC<{layer: Layer}>> = {Cut, Slice, Bars, YearRule, Twine, Tile, Tag, Tub, Tape, Scale, Words};

/** Words are set on the frame, not in the scene: the camera never moves them. */
const UNMOVED = new Set(['Words']);

type View = {scale: number; at: [number, number]; to: [number, number]};
type Pt = [number, number];
/** The scene point a view puts at the middle `mid` of the frame. */
const centreOf = (v: View, mid: Pt): Pt => [v.at[0] + (mid[0] - v.to[0]) / v.scale, v.at[1] + (mid[1] - v.to[1]) / v.scale];

/**
 * A beat's framing of the scene. With `view` {scale, at: [x, y], to: [X, Y]} the point `at` of the scene (px of the board's format)
 * sits at `to` on screen, enlarged by `scale`: a shot of one part of a composition another beat shows whole. With
 * `viewTo` as well, the camera moves from the one framing to the other over `viewMove` [start, length] in musical
 * beats, easing in and out, the scale changing by the same ratio every frame.
 * `drift` is a steady push on top of either, about the middle of the frame: the scale grows by that fraction evenly
 * over the beat, from `driftFrom` (a beat continuing the one before it starts where that one ended).
 */
const useFraming = (beat: Beat & {view?: View; viewTo?: View; viewMove?: [number, number]; drift?: number; driftFrom?: number}) => {
  const frame = useCurrentFrame();
  const {pulse, duration} = useMotion();
  const {width, height} = useVideoConfig();
  const MID: Pt = [width / 2, height / 2];
  const k = 1 + (beat.driftFrom ?? 0) + (beat.drift ?? 0) * Math.min(1, frame / Math.max(1, duration));
  const v = beat.view;
  if (!v) return {transform: k === 1 ? undefined : `scale(${k})`};
  let s = v.scale * k;
  let [cx, cy] = centreOf(v, MID);
  if (beat.viewTo) {
    const [m0, mb] = beat.viewMove ?? [0, 1];
    const t = Math.max(0, Math.min(1, (frame - m0 * pulse) / Math.max(1, mb * pulse)));
    const e = t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    const [dx, dy] = centreOf(beat.viewTo, MID);
    s = s * Math.pow((beat.viewTo.scale * k) / s, e);
    cx += (dx - cx) * e;
    cy += (dy - cy) * e;
  }
  return {transform: `translate(${MID[0] - s * cx}px, ${MID[1] - s * cy}px) scale(${s})`, transformOrigin: '0 0'};
};

const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const framing = useFraming(beat);
  return (
    <Move>
      {beat.layers.map((l, i) => {
        const C = KINDS[l.kind];
        if (!C) {
          console.log(`UNKNOWN_KIND ${l.kind}`);
          return null;
        }
        return (
          <AbsoluteFill key={i} style={UNMOVED.has(l.kind) || l.fixed ? undefined : framing}>
            <C layer={{id: `${beat.id}-${i}`, ...l}} />
          </AbsoluteFill>
        );
      })}
    </Move>
  );
};

export const Film: React.FC<FilmProps> = ({board, clips}) => {
  let start = 0;
  const seqs = board.beats.map((b, i) => {
    const frames = framesOf(b, board, board.format.fps);
    const exit = board.beats[i + 1]?.transition ?? null;
    const hold = exit?.preset === 'dissolve' ? exit.frames ?? 8 : 0;
    const from = start;
    start += frames;
    return (
      <Sequence key={b.id} from={from} durationInFrames={frames + hold}>
        <BeatProvider beat={b} enter={b.transition ?? null} exit={exit}>
          <BeatView beat={b} />
        </BeatProvider>
      </Sequence>
    );
  });
  return (
    <SystemProvider value={{system: board.system, board, format: (board.format as {name?: string}).name ?? 'reel', still: false}}>
      <FontGate system={board.system}>
        <AbsoluteFill data-frame style={{background: board.system.colors.bg}}>
          {board.tone === 'drive' ? <DriveFilm board={board} clips={clips ?? []} /> : seqs}
          {board.tone === 'drive' ? null : <Finish />}
        </AbsoluteFill>
      </FontGate>
    </SystemProvider>
  );
};
