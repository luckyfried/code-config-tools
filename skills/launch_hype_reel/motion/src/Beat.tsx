import React from 'react';
import {ClipShot} from './components/ClipShot';
import {DateCard} from './components/DateCard';
import {Hook} from './components/Hook';
import {Tease} from './components/Tease';
import type {Beat} from './types';

const KINDS = {Hook, Tease, DateCard, ClipShot};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
