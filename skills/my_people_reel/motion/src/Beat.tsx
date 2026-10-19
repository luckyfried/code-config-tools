import React from 'react';
import {ClipShot} from './components/ClipShot';
import {Grid} from './components/Grid';
import {Leaderboard} from './components/Leaderboard';
import {Opener} from './components/Opener';
import {Portrait} from './components/Portrait';
import type {Beat} from './types';

const KINDS = {Opener, ClipShot, Grid, Leaderboard, Portrait};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
