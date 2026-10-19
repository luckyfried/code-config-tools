import React from 'react';
import {Composition} from 'remotion';
import {Film, filmFrames, PostCard, Sheet, sheetHeight} from './Film';
import sample from '../sample/storyboard.json';
import type {Board, FilmProps, PostProps, SheetProps} from './types';

const board = sample as unknown as Board;

export const Root: React.FC = () => (
  <>
    <Composition
      id="Film"
      component={Film as React.FC<any>}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={450}
      defaultProps={{board} satisfies FilmProps}
      calculateMetadata={({props}) => {
        const b = (props as FilmProps).board;
        return {durationInFrames: Math.max(1, filmFrames(b)), width: b.format.width, height: b.format.height, fps: b.format.fps};
      }}
    />
    <Composition
      id="Post"
      component={PostCard as React.FC<any>}
      width={1080}
      height={1350}
      fps={30}
      durationInFrames={1}
      defaultProps={{board, post: board.posts[0]} satisfies PostProps}
    />
    <Composition
      id="Sheet"
      component={Sheet as React.FC<any>}
      width={1080}
      height={sheetHeight(7)}
      fps={30}
      durationInFrames={1}
      defaultProps={{board, rows: 7} satisfies SheetProps}
      calculateMetadata={({props}) => ({width: 1080, height: sheetHeight((props as SheetProps).rows ?? 7), durationInFrames: 1, fps: 30})}
    />
  </>
);
