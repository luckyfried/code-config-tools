import React from 'react';
import {AbsoluteFill} from 'remotion';
import {FontGate, SystemProvider} from '../system/system';
import type {FilmProps} from '../system/types';
import {DriveFilm} from './drive/DriveFilm';

/** The transformation film: the drive storyboard through one camera, under the board's type system and its finish. */
export const Film: React.FC<FilmProps> = ({board, clips}) => (
  <SystemProvider value={{system: board.system}}>
    <FontGate system={board.system}>
      <AbsoluteFill data-frame style={{background: board.system.colors.bg}}>
        <DriveFilm board={board} clips={clips ?? []} />
      </AbsoluteFill>
    </FontGate>
  </SystemProvider>
);
