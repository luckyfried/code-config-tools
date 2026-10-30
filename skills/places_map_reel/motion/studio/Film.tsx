import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FontGate, SystemProvider} from '../system/system';
import type {FilmProps} from '../system/types';
import {RouteFilm} from './route/RouteFilm';

/** The places film: the board's route through one camera over the map, under the style card's type and finish. */
export const Film: React.FC<FilmProps> = ({board, clips}) => (
  <SystemProvider value={{system: board.system}}>
    <FontGate system={board.system}>
      <AbsoluteFill data-frame style={{background: board.system.colors.bg}}>
        <RouteFilm board={board} clips={clips ?? []} />
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);
