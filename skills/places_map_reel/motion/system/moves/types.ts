// What a move, a cut, and a closer are given and what they give back. A move plays over one beat: it may nudge the
// camera's framing, add to the travel pass, and draw over the picture. A cut plays around the moment one beat gives way
// to the next: it says whether the camera jumps or travels, and may draw over the picture and add to the travel pass. A
// closer draws the film's last frame. Every word any of them sets is a word of the board: the beat's words and label,
// the title, the handle, the sign-off.
import type React from 'react';
import type {Travel} from '../three/travel';

/** One beat as a move sees it. */
export type BeatOn = {
  id: string;
  form: string;
  /** the beats it starts and ends on, from the film's start */
  at: number;
  end: number;
  move?: string;
  transition?: string | null;
  /** the beat's words and its label, as the person gave them; empty when it has none */
  words: string;
  label: string;
  peak: boolean;
  /** on a photo beat: where the photograph stands in the frame while the camera holds on it, [x0, y0, x1, y1] px; where
   * the beat's label and line stand, the same way (absent when it has none); and the beats the camera holds on it,
   * from its arrival to the pull back to the wall */
  box?: [number, number, number, number];
  type?: [number, number, number, number];
  held?: [number, number];
  /** on a photo beat: the address of its photograph, where it lies in the frame while the camera holds on it [x, y, w,
   * h] px, and the words its form sets on it (its label, else its line) */
  photo?: string;
  place?: [number, number, number, number];
  say?: string;
};

/** The tones the card gives every role a move, a cut, or a closer draws in, each a hex: the ground the beats lie on,
 * the dip a cut goes through (null: the card's cuts never dip), the matte of the bars, a gate's edge and a dark closer,
 * the light of a flash, a burn, a leak or a flare, the hand's pen, a print's rim, and the tape. */
export type Tones = {ground: string; dip: string | null; matte: string; light: string; pen: string; rim: string; tape: string};

/** The card's layout grid in frame px: its margin, and the lines of its columns and rows from edge to edge of the
 * measure; `rules` says where the card shows them (never across a photograph). */
export type Grid = {m: number; cols: number[]; rows: number[]; rules: 'none' | 'margins' | 'gutters'};

/** The film around every move: the frame, the card's colors and faces, the board's own words. */
export type Look = {
  W: number;
  H: number;
  fps: number;
  /** frames per musical beat */
  pulse: number;
  colors: Record<string, string>;
  display: string;
  text: string;
  /** whether the display face has an italic */
  italic: boolean;
  title: string;
  handle: string;
  signoff: string;
  tone: Tones;
  grid: Grid;
  /** the card's print: its portrait picture box on the frame, [x, y, w, h] px, its rim px, its tilt in degrees
   * clockwise, and the strips of tape that hold it */
  print: {box: [number, number, number, number]; rim: number; tilt: number; tape: number};
  /** whether the card's words take the film's finish or stand clean above it */
  finished: boolean;
  /** the address of the photograph the film's ground is made from, sharp; absent when the film has none */
  photo?: string;
  /** the address of every photograph the film has, in the board's order; absent when the kit lists none */
  photos?: string[];
};

/** A move at beat `t` of the film: `u` its progress through its beat, 0 to 1, and `local` the beats since it began. */
export type MoveProps = {beat: BeatOn; look: Look; u: number; local: number; t: number; seed: number};

/** How a move turns the camera's framing: `scale` multiplies the framed height (below 1 pushes in), `dx` and `dy` move
 * the framed middle by shares of the framed height, `roll` turns it, radians. */
export type Nudge = {scale?: number; dx?: number; dy?: number; roll?: number};

export type Move = {
  nudge?: (p: MoveProps) => Nudge;
  fx?: (p: MoveProps) => Partial<Travel>;
  Overlay?: React.FC<MoveProps>;
};

/** A cut at beat `t`: `u` its progress through its window, 0 to 1, the window centred on the moment of the cut. */
export type CutProps = {into: BeatOn; look: Look; u: number; t: number};

export type Cut = {
  /** the cut's window, in musical beats */
  beats: number;
  /** a jump changes the framing at the moment of the cut; a travel moves the camera from one beat to the next */
  jump: boolean;
  fx?: (p: CutProps) => Partial<Travel>;
  Overlay?: React.FC<CutProps>;
};

/** The closer at beat `local` since the closer began, `u` its progress to the stop. */
export type CloserProps = {look: Look; local: number; u: number};
export type CloserShape = React.FC<CloserProps>;
