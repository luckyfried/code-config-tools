import React from 'react';
import {ClipShot} from './components/ClipShot';
import {Closer} from './components/Closer';
import {Day} from './components/Day';
import {Montage} from './components/Montage';
import {Opener} from './components/Opener';
import {Postcard} from './components/Postcard';
import {Route} from './components/Route';
import type {Beat} from './types';

const KINDS = {Opener, Route, Day, Montage, Postcard, ClipShot, Closer};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
