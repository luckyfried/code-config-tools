import React from 'react';
import {ClipShot} from './components/ClipShot';
import {Feed} from './components/Feed';
import {Opener} from './components/Opener';
import type {Beat} from './types';

const KINDS = {Opener, ClipShot, Feed};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
