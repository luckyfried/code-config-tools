// slow-push: the camera eases in over the whole beat, a little, never stopping.
import {SINE} from '../kit';
import type {Move} from '../types';

export default {nudge: ({u}) => ({scale: 1 - 0.07 * SINE(u)})} satisfies Move;
