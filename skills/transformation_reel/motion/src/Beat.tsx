import React from 'react';
import {Chapter} from './components/Chapter';
import {ClipShot} from './components/ClipShot';
import {Dated} from './components/Dated';
import {Opener} from './components/Opener';
import {Split} from './components/Split';
import type {Beat} from './types';

const KINDS = {Opener, ClipShot, Dated, Split, Chapter};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
