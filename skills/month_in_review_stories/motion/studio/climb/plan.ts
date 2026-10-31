// The reel's plan as the board builder wrote it (scripts/compose/reel.py): every place in px of the closer's frame (the
// wall, y down), every time in musical beats from the film's start. The line's height is a track on the wall; the
// scale the camera holds and how far the closer's photographs stand out are worked out here from the beat, so any frame
// renders alone.
import {staticFile} from 'remotion';
import {bezier, clamp01, lerp, span, type Pt} from '../../system/three/motion';
import {at, type Track} from '../story/plan';
import type {Timeline} from '../../system/moves/layer';
import type {Look} from '../../system/moves/types';
import type {System} from '../../system/types';

export type Line = {
  text: string; x: number; y: number; size: number; face?: string; weight?: number; color?: string; anchor?: string; name?: string;
  /** the card's tracking for the line's face, em */
  tracking?: number;
  /** the font file the line is set in (the look's family) */
  file?: string;
  /** a count counts up from zero, from beat `at` over `beats` */
  tally?: {at: number; beats: number};
  /** the line lands word by word from beat `at`, a word every `step` beats (else the reel's `enter.step`), and leaves
   * the same way from `out` */
  at?: number;
  step?: number;
  out?: number;
  /** the long shadow's strength under the line, 0 to 1, when the board gives it one */
  shadow?: number;
};
export type Xf = {s: number; o: Pt};
export type Box = [number, number, number, number];

export type Card = {
  key: string;
  day: number;
  /** the month's peak moment: its card holds longest */
  peak: boolean;
  /** the moment's post's cell on the closer's wall, wall px; for a moment with no photograph, the band it is held on */
  cell: Box;
  /** the photograph sets into its cell and stays; a moment with no photograph leaves the wall as the camera does */
  stays: boolean;
  /** the line's climb on the wall: [foot, top], the cell's bottom and its top */
  line: [number, number];
  file: string | null;
  /** the photograph laid over its band, card px */
  place: Box;
  /** the band of the card the photograph fills, [top, foot] in card px; the ground is above and below it */
  band: [number, number];
  T: Xf;
  arrive: number;
  leave: number;
  /** when the line starts climbing and for how many beats */
  rise: [number, number];
  lines: Line[];
  /** where the words stand on the field under the band, card px: the field darkens softly behind them */
  strip: Box;
  /** how the camera holds on the card: pushing in, pulling back, or rising, each turning about the print its own way */
  hold: 'push' | 'pull' | 'crane';
  /** the photograph's subject, card px: the photograph eases about it over the hold */
  focus: Pt;
  /** the camera's move from this card to the next (to the closer from the last), [start, end] in beats */
  move: [number, number];
};

/** One of the month's posts on the closer's wall: its photograph's cell, its day beneath it, and when it rises out of
 * the wall. A moment's photograph is its card, set into the cell; another post's is `file`, cut to `crop` ([x, y, w, h],
 * fractions of the photograph from its top left). */
export type Tile = {day: number; cell: Box; moment: boolean; at: number; label: Line; file?: string; crop?: [number, number, number, number]};

export type Reel = {
  bpm: number;
  fps: number;
  W: number;
  H: number;
  /** the safe area's margins, px of the frame: nothing that must read stands outside them */
  safe: {top: number; bottom: number; left: number; right: number};
  frames: number;
  end: number;
  /** the furthest a hold pushes in on its card */
  zoom: number;
  /** a line lands word by word: a word every `step` beats, each settled in `beats` */
  enter: {step: number; beats: number};
  colors: Record<string, string>;
  /** the foot of the closer's wall */
  floor: number;
  /** the line's height on the wall, beat by beat */
  line: Track;
  cards: Card[];
  /** the beats the style card's moves and cuts play over, in musical beats: each moment's card, then the closer */
  timeline: Timeline;
  /** the board's own words the moves and the closing page set: the month's line, the handle, the sign-off; and the
   * card's face families */
  look: {title: string; handle: string; signoff: string; display: string; text: string; italic: boolean};
  closer: {
    at: number; top: number; land: number; words: number; sign: number; still: number;
    /** the card's closing page and when it comes over the wall, in beats */
    page: {name: string; at: number; still: number};
    /** the line's run under the wall: [x0, x1] */
    rule: [number, number];
    lines: Line[]; tiles: Tile[];
  };
};

/** A card's color, a role or a hex, as a hex. */
const toneOf = (r: Reel, v: string) => {
  const hex = r.colors[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** What the moves, cuts, and the closing page are given: the frame, the beat in frames, the colors, the card's tones,
 * grid, print and faces, whether its words take the finish, the month's first photograph, and the board's own words. */
export const lookOf = (r: Reel, sys: System): Look => {
  const {finish, photo} = sys;
  const g = photo.grid;
  const pic = photo.picture;
  const m = g.margin * r.W;
  const first = r.cards.find((c) => c.file);
  return {
    W: r.W, H: r.H, fps: r.fps, pulse: pulseOf(r), colors: r.colors, ...r.look,
    tone: {
      ground: toneOf(r, photo.ground), dip: finish.dip === 'none' ? null : toneOf(r, finish.dip),
      matte: toneOf(r, finish.matte), light: toneOf(r, finish.light), pen: toneOf(r, pic.penColor),
      rim: toneOf(r, pic.rimColor), tape: toneOf(r, pic.tapeColor),
    },
    grid: {
      m, rules: g.rules,
      cols: Array.from({length: g.cols + 1}, (_, i) => m + (i * (r.W - 2 * m)) / g.cols),
      rows: Array.from({length: g.rows + 1}, (_, i) => m + (i * (r.H - 2 * m)) / g.rows),
    },
    finished: finish.words !== 'clean',
    photo: first?.file ? staticFile(first.file) : undefined,
    print: {
      box: [Math.max(0, pic.box[0]) * r.W, Math.max(0, pic.box[1]) * r.H,
        (Math.min(1, pic.box[0] + pic.box[2]) - Math.max(0, pic.box[0])) * r.W, (Math.min(1, pic.box[1] + pic.box[3]) - Math.max(0, pic.box[1])) * r.H],
      rim: pic.rim * r.W, tilt: pic.tilt, tape: pic.tape,
    },
  };
};

export const onWall = (T: Xf, p: Pt): Pt => [T.o[0] + T.s * p[0], T.o[1] + T.s * p[1]];
export const pulseOf = (r: Reel) => (r.fps * 60) / r.bpm;
/** The closer's frame: the wall itself. */
export const WALL_T: Xf = {s: 1, o: [0, 0]};

/** The line's height on the wall at beat `t`: the board's track, except on a move from card to card, where it travels
 * with the camera, keeping its place in the picture as it goes from where it rests on one card to where its act starts
 * on the next, so the camera and the line arrive together. */
export const lineYAt = (r: Reel, t: number) => {
  const cs = r.cards;
  for (let i = 0; i + 1 < cs.length; i++) {
    const [a, b] = cs[i].move;
    if (t <= a || t >= b) continue;
    const A = cs[i].T, B = cs[i + 1].T;
    const ra = (at(r.line, a, r.floor) - A.o[1]) / (r.H * A.s);
    const rb = (at(r.line, b, r.floor) - B.o[1]) / (r.H * B.s);
    const u = MOVE((t - a) / (b - a));
    return lerp(A.o[1], B.o[1], u) + r.H * A.s * Math.pow(B.s / A.s, u) * lerp(ra, rb, u);
  }
  return at(r.line, t, r.floor);
};

/** How far the scene's overlay (the line and the words) is scaled and raised: a card's at its scale, the closer's wall
 * at 1; the camera's moves between them carry it over. `z` is the depth of the card's field, `print` of its print and
 * the line on it, and the line runs from x0 to x1: the band's width on a card, the wall's in the closer. */
export type State = {s: number; z: number; print: number; x0: number; x1: number};

export const liftOf = (s: number) => 90 * s;

/** The lens on a card: the camera holds a card's print filling the frame through a FOV-degree lens, DIST card px from it. */
export const FOV = 30;
export const distOf = (r: {H: number}) => r.H / 2 / Math.tan((FOV * Math.PI) / 360);
/** How far, card px, a card's print stands in front of its field, and its words in front of the print: the layers the
 * camera's turn separates. Each layer is scaled about the card's middle so that, seen from the card's station, it lands
 * where the board placed it. */
export const PRINT = 360;
export const LEAD = 100;

const cardState = (r: Reel, c: Card): State => ({s: c.T.s, z: liftOf(c.T.s), print: liftOf(c.T.s) + PRINT * c.T.s, x0: c.T.o[0], x1: c.T.o[0] + r.W * c.T.s});
const closerState = (r: Reel): State => ({s: 1, z: 1.2, print: 1.2, x0: r.closer.rule[0], x1: r.closer.rule[1]});
const mixState = (a: State, b: State, u: number): State => ({s: a.s * Math.pow(b.s / a.s, u), z: lerp(a.z, b.z, u), print: lerp(a.print, b.print, u),
  x0: lerp(a.x0, b.x0, u), x1: lerp(a.x1, b.x1, u)});

/** How deep a moment's cell stands out of the wall with its photograph on its face, and how deep the other posts' stand. */
export const DEPTH = 70;
export const DAY_DEPTH = 24;
const ENTER = bezier([0.22, 1.25, 0.36, 1]);

/** How far the moments' cells stand out of the wall at beat `t`, in px: none until the pull back is underway, all of
 * DEPTH (with an overshoot that settles) on the land. Their photographs and days ride the faces. */
export const standOutAt = (r: Reel, t: number) => {
  const a = r.closer.at + 0.4;
  return DEPTH * ENTER(clamp01((t - a) / (r.closer.land - a)));
};

/** How far a post's cell has risen out of the wall at beat `t`, 0 to 1 with an overshoot. */
export const risenAt = (tile: Tile, t: number) => ENTER(clamp01((t - tile.at) / 0.5));

/** The camera's moves between holds, [start, end] in beats, as the board wrote them on each card: card to card, the
 * last card to the closer. */
export const movesOf = (r: Reel) => r.cards.map((c) => ({a: c.move[0], b: c.move[1]}));

/** The camera's move from hold to hold, 0 to 1 over the move: it goes from where the wind-up left it, runs past its
 * landing and settles back onto it. */
const GO = bezier([0.45, 0, 0.3, 1.22]);
export const MOVE = (u: number) => (u <= 0 ? 0 : u >= 1 ? 1 : GO(u));

/** The wind-up before a move: over the last WINDUP beats of a hold the camera draws back against the way it is about to
 * go, BACK of the move (sideways by BACK of the distance, in or out by BACK of the change of scale), and comes to rest
 * there, so the back-off reads on its own before the move's blur starts. 0 to 1 at beat `t` before card `i`'s move. */
export const WINDUP = 0.9;
export const BACK = 0.1;
export const windAt = (r: Reel, i: number, t: number) => {
  const u = clamp01((t - (r.cards[i].move[0] - WINDUP)) / WINDUP);
  return (1 - Math.cos(Math.PI * u)) / 2;
};

/** How far card `i` has flown in at beat `t`, 0 to 1 with an overshoot, and when it starts: the first card stands at
 * its rest from the film's first frame, so the reel opens on a settled picture; another flies in from FLY_AT of the
 * move that brings the camera to it, over the one before as that trims into its cell, so a photograph fills the frame
 * through the whole move and the ground never shows bare between them. */
const FLY = bezier([0.12, 0.8, 0.3, 1.15]);
const FLY_AT = 0.32;
export const flyFrom = (r: Reel, i: number) => (i === 0 ? 0 : lerp(r.cards[i - 1].move[0], r.cards[i - 1].move[1], FLY_AT));
export const flyAt = (r: Reel, i: number, t: number) => {
  if (i === 0) return 1;
  const [a, b] = r.cards[i - 1].move;
  return span(t, lerp(a, b, FLY_AT), (1 - FLY_AT) * (b - a), FLY);
};
/** How far card `i`'s print has trimmed into its cell at beat `t`, 0 to 1: from the move's first third, as the
 * camera goes and the next card starts flying in. */
const TRIM = bezier([0.7, 0, 0.2, 1]);
export const trimAt = (r: Reel, i: number, t: number) => {
  const [a, b] = r.cards[i].move;
  return span(t, lerp(a, b, 0.3), 0.45 * (b - a), TRIM);
};
/** The last move's shares where the line has drawn back into its cell and where it starts to run out under the wall
 * (scripts/compose/reel.py LINE_OUT). */
export const LINE_OUT = [0.8, 0.88];
/** The card the line is on at beat `t`: each from when it starts flying in. */
export const lineCardAt = (r: Reel, t: number) => {
  let i = 0;
  while (i + 1 < r.cards.length && t >= flyFrom(r, i + 1)) i++;
  return i;
};
/** Where a card's print rests once it is in its cell: a hair over the cards before it. */
export const restZ = (index: number) => 0.03 * (index + 1);
/** How far card `i`'s print stands off the wall at beat `t`: PRINT over its field, coming down to its rest as it trims
 * into its cell, and standing out with the closer's moments. */
export const printZAt = (r: Reel, i: number, t: number) => {
  const s = r.cards[i].T.s;
  return lerp(liftOf(s) + PRINT * s, restZ(i), trimAt(r, i, t)) + standOutAt(r, t);
};
/** Where the line runs across at beat `t`, [x0, x1] on the wall: the width of the frame the camera holds, so it travels
 * with the camera through every move from card to card; on the last move it stays over the last print as that trims into
 * its cell, draws back into the cell's right corner, drops under the wall unseen (the board's track) and runs out along
 * the wall's foot from its left end. */
export const lineSpanAt = (r: Reel, t: number): [number, number] => {
  const cs = r.cards;
  if (!cs.length) return r.closer.rule;
  const c = cs[cs.length - 1];
  const [a, b] = c.move;
  if (t < a) {
    const st = stateAt(r, t);
    return [st.x0, st.x1];
  }
  const k = trimAt(r, cs.length - 1, t);
  const x0 = lerp(c.T.o[0], c.cell[0], k);
  const x: [number, number] = [x0, lerp(c.T.o[0] + r.W * c.T.s, c.cell[2], k)];
  const back = span(t, lerp(a, b, LINE_OUT[0] - 0.2), 0.2 * (b - a));
  const out = span(t, lerp(a, b, LINE_OUT[1]), (1 - LINE_OUT[1]) * (b - a) + 0.4);
  if (out <= 0) return [lerp(x[0], x[1], back), x[1]];
  return [r.closer.rule[0], lerp(r.closer.rule[0], r.closer.rule[1], out)];
};

export const stateAt = (r: Reel, t: number): State => {
  const cs = r.cards;
  const states = [...cs.map((c) => cardState(r, c)), closerState(r)];
  const moves = movesOf(r);
  for (let i = 0; i < moves.length; i++) {
    const m = moves[i];
    if (t < m.a) return states[i];
    if (t < m.b) return mixState(states[i], states[i + 1], MOVE(clamp01((t - m.a) / (m.b - m.a))));
  }
  return states[states.length - 1];
};
