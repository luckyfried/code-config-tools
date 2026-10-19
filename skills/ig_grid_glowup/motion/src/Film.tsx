import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {TransitionSeries} from '@remotion/transitions';
import {BeatView} from './Beat';
import {BeatProvider, FontGate, SystemProvider} from './system';
import {Finish} from './texture';
import {transitionFor} from './transitions';
import {PostView} from './components/Post';
import {Profile, profileHeight} from './components/Feed';
import type {Board, FilmProps, PostProps, SheetProps} from './types';

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

/** One of the next nine posts as a still, 1080 by 1350. */
export const PostCard: React.FC<PostProps> = ({board, post}) => (
  <SystemProvider value={{system: board.system, board, format: 'post', still: true}}>
    <FontGate system={board.system}>
      <AbsoluteFill style={{background: board.system.colors.bg}}>
        <PostView post={post} />
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);

/** The direction's style sheet: their profile with the next nine in place over the real grid. */
export const Sheet: React.FC<SheetProps> = ({board, rows}) => (
  <SystemProvider value={{system: board.system, board, format: 'post', still: true}}>
    <FontGate system={board.system}>
      <AbsoluteFill style={{background: '#fff'}}>
        <Profile posts={board.posts} rows={rows} divider />
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);

export const sheetHeight = (rows: number) => profileHeight(rows * 3) + 64;
