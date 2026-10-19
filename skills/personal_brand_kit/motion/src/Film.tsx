import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {TransitionSeries} from '@remotion/transitions';
import {BeatView} from './Beat';
import {GuideCard} from './components/GuideCard';
import {BeatProvider, FontGate, SystemProvider} from './system';
import {Finish} from './texture';
import {transitionFor} from './transitions';
import type {Board, CardProps, FilmProps} from './types';

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

/** One guide card as a 1080x1350 still, in the board's system. */
export const Card: React.FC<CardProps> = ({board, card}) => {
  const c = board.cards.find((x) => x.n === card) ?? board.cards[0];
  return (
    <SystemProvider value={{system: board.system, board, format: 'guide', still: true}}>
      <FontGate system={board.system}>
        <AbsoluteFill style={{background: board.system.colors.card}}>
          <GuideCard card={c} settled />
          <Finish />
        </AbsoluteFill>
      </FontGate>
    </SystemProvider>
  );
};
