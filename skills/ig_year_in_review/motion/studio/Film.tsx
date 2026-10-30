import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FontGate, SystemProvider} from '../system/system';
import type {FilmProps} from '../system/types';
import {YearFilm} from './year/YearFilm';

/** The year-in-review film: the board through one camera, under the board's style card: its faces, its finish, its closer. */
export const Film: React.FC<FilmProps> = ({board, clips}) => (
  <SystemProvider value={{system: board.system}}>
    <FontGate system={board.system}>
      <AbsoluteFill data-frame style={{background: board.system.colors.bg}}>
        <YearFilm board={board} clips={clips ?? []} />
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);
