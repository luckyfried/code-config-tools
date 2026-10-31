import React from 'react';
import {FontGate, SystemProvider} from '../system/system';
import type {FilmProps} from '../system/types';
import {DriveFilm} from './drive/DriveFilm';

/** The film of a board: the drive film, in the look of the board's style card. */
export const Film: React.FC<FilmProps> = ({board, clips}) => (
  <SystemProvider value={{system: board.system}}>
    <FontGate system={board.system}>
      <DriveFilm board={board} clips={clips ?? []} />
    </FontGate>
  </SystemProvider>
);
