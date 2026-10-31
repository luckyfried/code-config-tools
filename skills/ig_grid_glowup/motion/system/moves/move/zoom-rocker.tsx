// zoom-rocker: the camcorder's zoom rocker pressed and let go: the picture zooms in steps, in, in, then back out one.
import type {Move} from '../types';

const STEPS = [1, 0.9, 0.8, 0.86];

export default {
  nudge: ({local}) => ({scale: STEPS[Math.min(STEPS.length - 1, Math.floor(local * 1.5))]}),
} satisfies Move;
