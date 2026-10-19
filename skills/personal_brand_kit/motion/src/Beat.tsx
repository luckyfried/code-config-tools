import React from 'react';
import {ClipShot} from './components/ClipShot';
import {Opener} from './components/Opener';
import {Poster} from './components/Poster';
import {Reveal} from './components/Reveal';
import {Swipe} from './components/Swipe';
import type {Beat} from './types';

const KINDS = {Opener, ClipShot, Reveal, Swipe, Poster};

export const BeatView: React.FC<{beat: Beat}> = ({beat}) => {
  const C = KINDS[beat.kind];
  if (!C) {
    console.log(`UNKNOWN_KIND ${beat.kind}`);
    return null;
  }
  return <C beat={beat} />;
};
