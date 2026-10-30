import React from 'react';
import {Composition} from 'remotion';
import {framesOf} from '../system/system';
import type {Board, FilmProps} from '../system/types';
import {Film} from './Film';

/** Frames the film runs: every beat end to end; each cut sits on its downbeat. */
const filmFrames = (board: Board) => board.beats.reduce((n, b) => n + framesOf(b, board, board.format.fps), 0);

/** The best-nine film, sized and timed by the board it is given. */
export const Root: React.FC = () => (
  <Composition
    id="Film"
    component={Film as React.FC<any>}
    width={1080}
    height={1920}
    fps={30}
    durationInFrames={300}
    defaultProps={{board: {id: 'empty', name: 'empty', handle: '', year: 2026, bpm: 120, style: 'swiss-grid', format: {width: 1080, height: 1920, fps: 30}, beats: []} as unknown as Board} satisfies FilmProps}
    calculateMetadata={({props}) => {
      const b = (props as FilmProps).board;
      return {durationInFrames: Math.max(1, filmFrames(b)), width: b.format.width, height: b.format.height, fps: b.format.fps};
    }}
  />
);
