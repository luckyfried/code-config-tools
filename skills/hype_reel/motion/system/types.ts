export type Face = {
  family: string;
  file: string;
  weight: number;
  tracking: number;
  case: 'none' | 'uppercase' | 'lowercase';
  lineHeight: number;
  /** variable-font axes set on the face, such as {"wdth": 68} for a condensed cut */
  axes?: Record<string, number>;
};

export type Ease = {
  enter: number[];
  exit: number[];
  move: number[];
  spring: {damping: number; stiffness: number; mass: number};
  hit: {damping: number; stiffness: number; mass: number};
  stagger: number;
};

export type Grade = {lift: [number, number, number]; gamma: number; gain: [number, number, number]; saturation: number};

/** The style card's finish: each value used as it is. */
export type Finish = {
  grain: number; vignette: number; bloom: number; dust: number; blur: number; halation: number; cadence: number; bars: number;
  burn: string; grade: Grade;
  /** the tone a cut dips through (a role or a hex), or `none`: the card's cuts never dip */
  dip: string;
  /** the tone of the letterbox bars, a gate's edge, and a closer's ground */
  matte: string;
  /** the tone of a flash, a burn, a leak, and a flare */
  light: string;
  /** `finished`: the grade and grain lie over the words too; `clean`: the words stand above the finish */
  words: 'finished' | 'clean';
};

/** The style card's photo layout: where a photo beat's photograph stands (shares of the frame), the ground around it,
 * and the face, size, color and entrance of its line and label. */
export type PhotoLayout = {
  picture: {show: boolean; box: [number, number, number, number]; rim: number; rimColor: string; tilt: number; tape: number; tapeColor: string;
    /** the ink of the hand that draws on the photograph */
    penColor: string};
  ground: string;
  line: {box: [number, number, number, number]; face: string; size: number; align: string; color: string; enter: string; rotate: number; scrim: number};
  label: {face: string; size: number; color: string};
  rule: boolean;
  /** the card's layout grid: columns and rows, the margin a share of the frame's width, and where its rules show */
  grid: {cols: number; rows: number; margin: number; rules: 'none' | 'margins' | 'gutters'};
  /** a landscape photograph's own layout on a tall frame: its picture box and its line box */
  landscape: {box: [number, number, number, number]; line: [number, number, number, number]};
};

export type System = {
  style: string;
  display: Face;
  text: Face;
  colors: Record<string, string> & {swatches?: {hex: string; name: string}[]};
  ease: Ease;
  finish: Finish;
  closer: string;
  photo: PhotoLayout;
  /** how the camera moves within a beat: slam, dolly or snap */
  camera: string;
};

/** A beat's photograph: its box on the frame [x, y, w, h], where it lies in the box (`place`, box px) and the point the
 * camera's moves center on (`focus`, box px); `fill`, the box's ground at its top and foot around a still laid whole
 * in a box it does not cover. */
export type Picture = {file: string; clip?: string; box: [number, number, number, number]; place: [number, number, number, number]; focus: [number, number];
  fill?: [string, string]};

/** A line of the beat's words: `top` the top of its line box and `x` its left (or middle, centered), frame px; `t` the
 * musical beat it lands on, from the beat's start; `color` a role of the board's colors. */
export type Line = {text: string; top: number; x: number; align: 'left' | 'center'; size: number; face: string; role: string; color: string; t: number; w: number;
  /** the line box the card sets a photo beat's words in, [x0, y0, x1, y1] frame px */
  box?: [number, number, number, number];
  /** the musical beat it leaves on, from the beat's start, where the next word lands in its place; absent, it holds to the cut */
  until?: number;
  /** on a field beat, the role of the field the line lands on, from its beat; absent, the beat's ground */
  ground?: string};

export type Beat = {
  id: string;
  part: string;
  form: string;
  /** length in musical beats */
  len: number;
  /** frames, set by snap from the music's beats */
  frames?: number;
  words: string;
  label: string;
  peak: boolean;
  move?: string | null;
  transition?: string | null;
  /** card: the card's photo layout; frame: the picture covers the frame; field: the ground covers it and the words
   * land one a beat on it; matte: the picture above, the words below it on the ground, the card's matte */
  layout: 'card' | 'frame' | 'field' | 'matte';
  picture: Picture | null;
  ground: string;
  lines: Line[];
  /** a field beat's words all at rest, the whole line as its still shows it */
  still?: Line[];
  scrim: number;
  enter: string;
  /** the closer's stop, in musical beats from its start */
  stop?: number;
};

export type Board = {
  id: string;
  name: string;
  handle: string;
  title: string;
  signoff: string;
  bpm: number;
  format: {width: number; height: number; fps: number; name?: string};
  system: System;
  beats: Beat[];
  sound?: {kind: string; at: number}[];
};

/** The frames of a clip shown in place of the photograph it was made from: `dir`/0001.jpg onward, from the film's frame `from`. */
export type Clip = {id: string; image: string; from: number; frames: number; dir: string};
export type FilmProps = {board: Board; clips?: Clip[]};
