import React from 'react';
import {ClipShot} from './components/ClipShot';
import {DayNight} from './components/DayNight';
import {MapJourney} from './components/MapJourney';
import {Opener} from './components/Opener';
import {Poster} from './components/Poster';
import {Stamp} from './components/Stamp';
import type {Beat} from './types';

const KINDS = {Opener, ClipShot, MapJourney, Stamp, DayNight, Poster};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
