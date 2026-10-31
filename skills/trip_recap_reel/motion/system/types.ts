export type Face = {
  family: string;
  file: string;
  weight: number;
  tracking: number;
  case: 'none' | 'uppercase' | 'lowercase';
  lineHeight: number;
  /** variable-font axes set on the face, such as {"wdth": 68} for a condensed cut */
  axes?: Record<string, number>;
  /** the face's italic file, when the card names one */
  italic?: string;
};

export type Ease = {
  enter: [number, number, number, number];
  exit: [number, number, number, number];
  move: [number, number, number, number];
  spring: {damping: number; stiffness: number; mass: number};
  hit: {damping: number; stiffness: number; mass: number};
  stagger: number;
  curve?: string;
  /** how far the camera leans into a sideways move, radians */
  lean?: number;
};

/** The finish the style card gives the picture: every value is the value, zero included. `cadence` is the frames a
 * second the picture steps at (0 moves on every frame); `bars` is each letterbox bar's height as a share of the frame. */
export type Finish = {
  grain: number;
  vignette: number;
  bloom: number;
  dust: number;
  blur: number;
  halation: number;
  cadence: number;
  bars: number;
  burn: string;
  grade: {lift: [number, number, number]; gamma: number; gain: [number, number, number]; saturation: number};
  /** the tone a cut dips through (a role or a hex), or `none`: the card's cuts never dip */
  dip: string;
  /** the tone of the letterbox bars, a gate's edge, and a closer's ground */
  matte: string;
  /** the tone of a flash, a burn, a leak, and a flare */
  light: string;
  /** `finished`: the grain and grade lie over the words too; `clean`: the words stand above the finish */
  words: 'finished' | 'clean';
};

/** How the card lays out a photo beat: where the photograph stands (frame shares), its rim, tilt and tape, the ground
 * around it, and the box (shares of the type area) its label and line are set in. */
export type PhotoLayout = {
  picture: {show: boolean; box: [number, number, number, number]; rim: number; rimColor: string; tilt: number; tape: number;
    tapeColor: string;
    /** the ink of the hand that draws on the photograph: a circle, an underline, a scribbled word */
    penColor: string};
  ground: string;
  line: {box: [number, number, number, number]; face: string; size: number; align: 'start' | 'center'; color: string;
    enter: 'rise' | 'slam' | 'type' | 'fade' | 'cut'; rotate: number; scrim: number};
  label: {face: string; size: number; color: string};
  rule: boolean;
  /** the card's layout grid: columns and rows, the margin a share of the frame's width, and where its rules show
   * (never across a photograph) */
  grid: {cols: number; rows: number; margin: number; rules: 'none' | 'margins' | 'gutters'};
  /** a landscape photograph's own layout on a tall frame: its picture box (frame shares) and its line box (shares of
   * the type area) */
  landscape: {box: [number, number, number, number]; line: [number, number, number, number]};
};

export type Safe = {top: number; bottom: number; left: number; right: number};

export type System = {
  /** the style card the board is made in (styles/<id>.json) */
  style: string;
  display: Face;
  text: Face;
  colors: {bg: string; ink: string; accent: string; accent2: string; muted: string; paper: string; swatches: {hex: string; name: string}[]};
  finish: Finish;
  /** the card's closer: the shape of the film's last frame (motion/system/moves/closer/<id>.tsx) */
  closer: string;
  photo: PhotoLayout;
  ease: Ease;
  safe: Record<string, Safe>;
};

/** One stop of the trip as the board places it: its photograph (or clip poster), the photograph's height over its
 * width, where the person stood (`near`) and what the frame looks at (`far`), as shares of the photograph. */
export type Stop = {
  name: string;
  place: string;
  city: string;
  photo: string;
  aspect: number;
  near: [number, number];
  far: [number, number];
  caption: string;
  date: string;
  clip?: boolean;
};

export type Beat = {
  id: string;
  /** title (the hook), photo, clip or closer */
  form: string;
  bars: number;
  /** the musical beats it starts and ends on, from the film's start; set by storyboard.py snap */
  at?: number;
  end?: number;
  frames?: number;
  /** frames per musical beat */
  pulse?: number;
  /** the beat's move and the cut into it, from the card's allowlists */
  move?: string | null;
  transition?: string | null;
  words: string;
  label: string;
  peak: boolean;
  /** the stops the beat shows, by index */
  stops: number[];
  anchor?: string | null;
};

export type Board = {
  id: string;
  style: string;
  name: string;
  bpm: number;
  format: {width: number; height: number; fps: number; name?: string};
  system: System;
  route: {title: string; kicker: string; stops: Stop[]; closer: {at: number; still: number}; signoff: string; handle: string};
  beats: Beat[];
  sound?: {kind: string; at: number}[];
};

/** A clip placed on the beat it plays on: its frames `dir`/0001.jpg onward, from the film's frame `from` for `frames`
 * film frames, `step` clip frames to each film frame. */
export type Clip = {id: string; beat?: string; image: string; from: number; frames: number; step?: number; dir: string};
export type FilmProps = {board: Board; clips?: Clip[]};
