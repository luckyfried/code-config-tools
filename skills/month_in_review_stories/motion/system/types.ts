import type {CardFinish} from './three/Stage';

/** One of the card's faces as the board carries it: the family, its font file (kit-relative), its weight, its tracking
 * in em, its case, and its line height. */
export type Face = {family: string; file: string; weight: number; tracking: number; case: string; lineHeight: number; italic?: string};

/** The board's look, drawn from its style card: the card's faces, the colors the palette rule made from their photographs
 * (roles bg, ink, paper, accent, accent2, muted), its easing, its finish, its closer, its photo layout, and the safe
 * area. */
export type System = {
  style: string;
  display: Face;
  text: Face;
  colors: Record<string, string>;
  ease: {lean?: number; [k: string]: unknown};
  finish: Finish;
  closer: string;
  photo: PhotoLayout;
  safe: {top: number; bottom: number; left: number; right: number};
};

/** The card's finish: the picture's grain, grade and the rest as the stage reads them, and the tones its cuts, bars and
 * lights are drawn in: `dip` the tone a cut goes through (a role or a hex, or `none`: the card's cuts never dip),
 * `matte` the bars, a gate's edge and a dark closer's ground, `light` a flash, burn, leak or flare; `words` says
 * whether the grain and grade lie over the words (`finished`) or the words stand above them (`clean`). */
export type Finish = CardFinish & {dip: string; matte: string; light: string; words: 'finished' | 'clean'};

/** The card's photo beat: its picture box (shares of the frame), rim, tilt, tape and pen, the ground around it, its
 * line's box (shares of the type area), its layout grid, and a landscape photograph's own picture and line boxes. */
export type PhotoLayout = {
  picture: {show: boolean; box: [number, number, number, number]; rim: number; rimColor: string; tilt: number; tape: number;
    tapeColor: string; penColor: string};
  ground: string;
  line: {box: [number, number, number, number]; face: string; size: number; align: 'start' | 'center'; color: string;
    enter: string; rotate: number; scrim: number};
  label: {face: string; size: number; color: string};
  rule: boolean;
  grid: {cols: number; rows: number; margin: number; rules: 'none' | 'margins' | 'gutters'};
  landscape: {box: [number, number, number, number]; line: [number, number, number, number]};
};

export type Board = {
  bpm: number;
  format: {width: number; height: number; fps: number};
  system: System;
};

/** A generated clip placed on the photograph it was made from: its frames `dir`/0001.jpg onward, from the film's frame `from`. */
export type Clip = {id: string; image: string; from: number; frames: number; dir: string};
