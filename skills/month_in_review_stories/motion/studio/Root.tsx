import React from 'react';
import {Composition} from 'remotion';
import {FontGate, SystemProvider} from '../system/system';
import type {Board, Clip} from '../system/types';
import {ClimbFilm} from './climb/ClimbFilm';
import type {Reel} from './climb/plan';
import type {Series} from './story/plan';
import {SeriesFilm, seriesFrames} from './story/Story';

type Props = {board: Board & Series & {reel?: Reel}; clips?: Clip[]};

const empty = {board: {bpm: 128, format: {width: 1080, height: 1920, fps: 30}, system: {colors: {}}, beats: []}} as unknown as Props;

/** The month's reel, the climb (`Reel`), drawn from `board.reel`. */
const ReelOf: React.FC<Props> = ({board, clips}) => (
  <SystemProvider value={{system: board.system, board, format: 'reel', still: false}}>
    <FontGate system={board.system}>
      <ClimbFilm reel={board.reel as Reel} clips={clips ?? []} />
    </FontGate>
  </SystemProvider>
);

/** The month's story cards end to end (`Film`), drawn from `board.beats`. */
const SeriesOf: React.FC<Props> = ({board}) => (
  <SystemProvider value={{system: board.system, board, format: 'story', still: false}}>
    <FontGate system={board.system}>
      <SeriesFilm board={board} />
    </FontGate>
  </SystemProvider>
);

/** The month's series (`Film`, every card) and its reel (`Reel`), sized and timed by the board they are given. */
export const Root: React.FC = () => (
  <>
    <Composition
      id="Film"
      component={SeriesOf as React.FC<any>}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={450}
      defaultProps={empty}
      calculateMetadata={({props}) => {
        const b = (props as Props).board;
        return {durationInFrames: Math.max(1, seriesFrames(b.beats)), width: b.format.width, height: b.format.height, fps: b.format.fps};
      }}
    />
    <Composition
      id="Reel"
      component={ReelOf as React.FC<any>}
      width={1080}
      height={1920}
      fps={30}
      durationInFrames={450}
      defaultProps={empty}
      calculateMetadata={({props}) => {
        const r = (props as Props).board.reel;
        return {durationInFrames: r?.frames ?? 1, width: r?.W ?? 1080, height: r?.H ?? 1920, fps: r?.fps ?? 30};
      }}
    />
  </>
);
