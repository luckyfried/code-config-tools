// The table's opening replay: a complete game, recorded move by move, that the page plays while setup is open. The
// opening runs fast; the last six moves play at full pace, with a pass, a thirteen-disc wave along three lines, and
// the counting wave at the end.
import { parseSquare } from "./reversi.js";

export const DEMO_MOVES = (
  "e6 d6 c3 f4 c4 e3 f3 c5 f6 d3 f5 e7 d8 b3 d7 f8 c6 g5 a3 c8 h6 c7 b6 a6 b4 h5 a5 e8 f7 e2 " +
  "d1 d2 c1 f2 h4 a4 f1 g4 g8 h8 h3 e1 g3 g1 h1 c2 b1 a2 b7 b5 b2 a8 b8 a7 g2 a1 g6 h7 h2 g7"
).split(" ").map(parseSquare);

/** How many moves play fast before the replay settles to full pace. */
export const DEMO_FAST = 54;

export const DEMO_TIMING = {
  hold: 300, // the opening four, still, before the first move
  fastStep: 40, // between fast moves
  fastPace: 0.4, // a fast move's speed against a full one
  slowStep: 660, // between full-pace moves
  preview: 340, // the ghost preview before each full-pace move
  afterEnd: 420, // the last move settling before the counting wave
  rest: 3600, // the result on screen before the replay starts over
};
