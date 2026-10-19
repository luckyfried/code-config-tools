import React from 'react';
import {Composition} from 'remotion';
import {Card, Film, filmFrames} from './Film';
import sample from '../sample/storyboard.json';
import type {Board, CardProps, FilmProps} from './types';

const board = sample as unknown as Board;

export const Root: React.FC = () => (
  <>
    <Composition
      id="Film"
      component={Film as React.FC<any>}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={300}
      defaultProps={{board, format: 'reel'} satisfies FilmProps}
      calculateMetadata={({props}) => {
        const p = props as FilmProps;
        const b = p.board;
        const wide = p.format === 'landscape';
        return {durationInFrames: Math.max(1, filmFrames(b)), width: wide ? 1920 : b.format.width, height: wide ? 1080 : b.format.height, fps: b.format.fps};
      }}
    />
    <Composition
      id="Card"
      component={Card as React.FC<any>}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={1}
      defaultProps={{board, beat: board.stories?.[0] ?? board.beats[0], format: 'story'} satisfies CardProps}
      calculateMetadata={({props}) => {
        const p = props as CardProps;
        return {width: 1080, height: p.format === 'square' ? 1080 : 1920, durationInFrames: Math.max(1, p.beat.frames), fps: 30};
      }}
    />
  </>
);
