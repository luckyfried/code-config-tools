import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FontGate, SystemProvider} from '../system/system';
import type {FilmProps} from '../system/types';
import {HypeFilm} from './film/HypeFilm';

/** The hype reel, under the board's style card. */
export const Film: React.FC<FilmProps> = ({board, clips}) => (
  <SystemProvider value={{system: board.system}}>
    <FontGate system={board.system}>
      <AbsoluteFill data-frame style={{background: board.system.colors.bg}}>
        <HypeFilm board={board} clips={clips ?? []} />
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);
