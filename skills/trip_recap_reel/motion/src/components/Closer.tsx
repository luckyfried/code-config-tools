import React from 'react';
import {CloserScene} from './Route';
import type {Beat} from '../types';

export const Closer: React.FC<{beat: Beat}> = ({beat}) => <CloserScene beat={beat} />;
