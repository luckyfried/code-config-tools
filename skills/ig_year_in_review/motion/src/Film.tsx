import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {TransitionSeries} from '@remotion/transitions';
import {BeatView} from './Beat';
import {BeatProvider, FontGate, SystemProvider} from './system';
import {Finish} from './texture';
import {transitionFor} from './transitions';
import type {Board, CardProps, FilmProps} from './types';
import {faceStyle, useSafe, useSys} from './system';

/** Frames the film runs: every beat, less the overlap of each transition into it. */
export const filmFrames = (board: Board) =>
  board.beats.reduce((n, b, i) => n + b.frames - (i > 0 && b.transition ? b.transition.frames : 0), 0);

export const Film: React.FC<FilmProps> = ({board}) => {
  const {width, height} = useVideoConfig();
  const items: React.ReactNode[] = [];
  board.beats.forEach((b, i) => {
    if (i > 0 && b.transition && b.transition.frames > 0) {
      const t = transitionFor(b.transition, board.system, width, height);
      items.push(<TransitionSeries.Transition key={`t-${b.id}`} presentation={t.presentation as any} timing={t.timing} />);
    }
    items.push(
      <TransitionSeries.Sequence key={b.id} durationInFrames={b.frames}>
        <BeatProvider beat={b}>
          <BeatView beat={b} />
        </BeatProvider>
      </TransitionSeries.Sequence>,
    );
  });
  return (
    <SystemProvider value={{system: board.system, board, format: 'reel', still: false}}>
      <FontGate system={board.system}>
        <AbsoluteFill style={{background: board.system.colors.bg}}>
          <TransitionSeries>{items}</TransitionSeries>
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

/** One card of the carousel or the story set: a beat at its settled frame, laid out for that format. */
export const Card: React.FC<CardProps> = ({board, beat, format, index, total}) => (
  <SystemProvider value={{system: board.system, board, format, still: true, beat}}>
    <FontGate system={board.system}>
      <AbsoluteFill style={{background: board.system.colors.bg}}>
        <BeatView beat={beat} />
        <Finish />
        {format === 'carousel' ? <PageMark index={index} total={total} /> : null}
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);
