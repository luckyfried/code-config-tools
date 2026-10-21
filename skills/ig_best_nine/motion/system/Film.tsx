import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {BeatView} from './Beat';
import {BeatProvider, faceStyle, FontGate, framesOf, SystemProvider, useSafe, useSys} from './system';
import {Finish} from './texture';
import type {Board, CardProps, FilmProps} from './types';

/** Frames the film runs: every beat end to end; each cut sits on its downbeat. */
export const filmFrames = (board: Board) => board.beats.reduce((n, b) => n + framesOf(b, board, board.format.fps), 0);

export const Film: React.FC<FilmProps> = ({board}) => {
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
    <SystemProvider value={{system: board.system, board, format: 'reel', still: false}}>
      <FontGate system={board.system}>
        <AbsoluteFill style={{background: board.system.colors.bg}}>
          {seqs}
          <Finish />
        </AbsoluteFill>
      </FontGate>
    </SystemProvider>
  );
};

const PageMark: React.FC<{index: number; total: number}> = ({index, total}) => {
  const s = useSafe();
  const {system} = useSys();
  if (total <= 1) return null;
  return (
    <div style={{position: 'absolute', right: s.right, top: s.top * 0.5, ...faceStyle(system.text), fontSize: system.scale.label * 0.8, textTransform: 'none',
      letterSpacing: '0.08em', color: system.colors.ink, opacity: 0.7}}>
      {String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}
    </div>
  );
};

/** One card of the carousel or the story set: a beat's stack at its settled frame, laid out for that format. */
export const Card: React.FC<CardProps> = ({board, beat, format, index, total}) => (
  <SystemProvider value={{system: board.system, board, format, still: true, beat}}>
    <FontGate system={board.system}>
      <AbsoluteFill style={{background: board.system.colors.bg}}>
        <BeatProvider beat={beat}>
          <BeatView beat={beat} />
        </BeatProvider>
        <Finish />
        {format === 'carousel' ? <PageMark index={index} total={total} /> : null}
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);
