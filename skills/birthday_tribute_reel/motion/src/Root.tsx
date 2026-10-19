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
      defaultProps={{board} satisfies FilmProps}
      calculateMetadata={({props}) => {
        const b = (props as FilmProps).board;
        return {durationInFrames: Math.max(1, filmFrames(b)), width: b.format.width, height: b.format.height, fps: b.format.fps};
      }}
    />
    <Composition
      id="Card"
      component={Card as React.FC<any>}
      width={1080}
      height={1350}
      fps={30}
      durationInFrames={1}
      defaultProps={{board, beat: board.card ?? board.beats[board.beats.length - 1], format: 'portrait'} satisfies CardProps}
      calculateMetadata={({props}) => {
        const p = props as CardProps;
        const height = {portrait: 1350, story: 1920, square: 1080}[p.format] ?? 1350;
        return {width: 1080, height, durationInFrames: Math.max(1, p.beat.frames), fps: 30};
      }}
    />
  </>
);
