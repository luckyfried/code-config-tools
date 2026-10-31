// lateral-dolly: the camera tracks sideways across the picture at an even speed, the way a dolly on rails does. It
// travels as far as its push leaves picture on either side, so a picture that fills the frame never shows its edge and
// the words laid on it stay inside the safe area on a tall frame as on a wide one.
import {SINE} from '../kit';
import type {Move} from '../types';

/** The push the dolly holds while it travels: the frame shows this share of the picture's height. */
const PUSH = 0.94;

export default {
  nudge: ({u, look}) => {
    const reach = 0.5 * (1 - PUSH) * (look.W / look.H);
    return {dx: reach * (2 * SINE(u) - 1), scale: PUSH};
  },
} satisfies Move;
