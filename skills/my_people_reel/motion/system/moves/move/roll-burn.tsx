// roll-burn (the move): the end of the roll: the picture runs on, then burns in from the left edge in the card's burn
// color as the beat ends, the picture still showing through.
import {span} from '../kit';
import type {Move} from '../types';

export default {fx: ({u}) => ({burn: 0.6 * span(u, 0.55, 0.45)})} satisfies Move;
