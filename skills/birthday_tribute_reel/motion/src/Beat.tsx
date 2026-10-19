import React from 'react';
import {ClipShot} from './components/ClipShot';
import {Closer} from './components/Closer';
import {Exchange} from './components/Exchange';
import {KineticType} from './components/KineticType';
import {Opener} from './components/Opener';
import {PhotoLive} from './components/PhotoLive';
import type {Beat} from './types';

const KINDS = {Opener, ClipShot, PhotoLive, KineticType, Exchange, Closer};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
