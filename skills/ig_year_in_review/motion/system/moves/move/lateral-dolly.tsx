// lateral-dolly: the camera tracks sideways across the picture at an even speed, the way a dolly on rails does.
import {SINE} from '../kit';
import type {Move} from '../types';

export default {nudge: ({u}) => ({dx: -0.07 + 0.14 * SINE(u), scale: 0.92})} satisfies Move;
