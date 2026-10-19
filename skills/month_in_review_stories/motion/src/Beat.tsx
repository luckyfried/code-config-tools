import React from 'react';
import {ClipShot} from './components/ClipShot';
import {Closer} from './components/Closer';
import {Diary} from './components/Diary';
import {KineticType} from './components/KineticType';
import {Mosaic} from './components/Mosaic';
import {Opener} from './components/Opener';
import {PhotoLive} from './components/PhotoLive';
import {StatCard} from './components/StatCard';
import type {Beat} from './types';

const KINDS = {Opener, ClipShot, StatCard, Mosaic, KineticType, PhotoLive, Closer, Diary};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
