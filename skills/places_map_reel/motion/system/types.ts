export type Face = {
  family: string;
  file: string;
  weight: number;
  tracking: number;
  case: 'none' | 'uppercase' | 'lowercase';
  lineHeight: number;
  /** variable-font axes set on the face, such as {"wdth": 68} for a condensed cut or {"opsz": 144, "SOFT": 100} */
  axes?: Record<string, number>;
  /** the face's italic file, when the card names one */
  italic?: string;
};

export type Ease = {
  enter: [number, number, number, number];
  exit: [number, number, number, number];
  move: [number, number, number, number];
  spring: {damping: number; stiffness: number; mass: number};
  /** the overshooting spring of a thing landing on a beat */
  hit: {damping: number; stiffness: number; mass: number};
  stagger: number;
  /** the card's curve family (bezier, spring, sine, quart, noise) and how far the camera leans into a move, radians */
  curve?: string;
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
  /** the tone a cut dips through (a role or a hex), or `none`: the card's cuts never dip */
  dip: string;
  /** the tone of the letterbox bars, a gate's edge, and a closer's ground */
  matte: string;
  /** the tone of a flash, a burn, a leak, and a flare */
  light: string;
  /** `finished`: the grain and grade lie over the words too; `clean`: the words stand above the finish */
  words: 'finished' | 'clean';
  grade: {lift: [number, number, number]; gamma: number; gain: [number, number, number]; saturation: number};
};

/** The card's photo beat: where its photograph stands and how it is dressed, the ground around it, and the box, faces,
 * sizes, colors and entrance of the label and the moment's line. Boxes are shares: the picture's of the frame (a side on
 * the frame's edge runs past it), the line's of the type area; sizes are px at 1080; colors are roles or hexes. */
export type PhotoLayout = {
  /** `show` false: no photograph on the beat, only the line on the ground; `rim` a share of the frame's width, `tilt`
   * degrees clockwise, `tape` the strips holding its top corners */
  picture: {show: boolean; box: [number, number, number, number]; rim: number; rimColor: string; tilt: number; tape: number;
    tapeColor: string;
    /** the ink of the hand that draws on the photograph: a circle, an underline, a scribbled word */
    penColor: string};
  ground: string;
  line: {box: [number, number, number, number]; face: string; size: number; align: 'start' | 'center'; color: string;
    enter: 'rise' | 'slam' | 'type' | 'fade' | 'cut'; rotate: number;
    /** how dark the photograph is shaded under the line, from clear above the label to this much black at its foot */
    scrim: number};
  label: {face: string; size: number; color: string};
  /** the line the dot draws stays on the photograph */
  rule: boolean;
  /** the card's layout grid: columns and rows, the margin a share of the frame's width, and where its rules show
   * (never across a photograph) */
  grid: {cols: number; rows: number; margin: number; rules: 'none' | 'margins' | 'gutters'};
  /** a landscape photograph's own layout on a tall frame: its picture box and its line box */
  landscape: {box: [number, number, number, number]; line: [number, number, number, number]};
};

export type Safe = {top: number; bottom: number; left: number; right: number};

export type System = {
  /** the style card the board is made in (styles/<id>.json) */
  style: string;
  display: Face;
  text: Face;
  scale: {hero: number; h1: number; h2: number; h3: number; body: number; label: number};
  colors: {
    bg: string;
    ink: string;
    accent: string;
    accent2: string;
    muted: string;
    paper: string;
    swatches: {hex: string; name: string}[];
  };
  finish: Finish;
  /** the card's closer: the shape of the film's last frame (motion/system/moves/closer/<id>.tsx) */
  closer: string;
  photo: PhotoLayout;
  ease: Ease;
  safe: Record<string, Safe>;
};

/**
 * One layer of a beat's stack. `at` is the musical beat (from the start of the beat) where the layer enters,
 * `out` the musical beat where it leaves (absent: it leaves with the cut; null: it holds through the cut).
 */
export type Layer = {
  kind: string;
  at?: number;
  out?: number | null;
  [prop: string]: any;
};

export type Beat = {
  id: string;
  /** the form this beat plays: the hook is a title, every stop a photograph, the last beat the closer */
  form?: string;
  /** length in bars of the track: 1, 2 or 4 */
  bars: number;
  /** frames, set by storyboard.py snap from the track's downbeats */
  frames?: number;
  /** frames per musical beat, set by snap from the track's tempo */
  pulse?: number;
  /** the beat's move and the cut into it, from its card's allowlists, chosen by the board from the beat's content */
  move?: string;
  transition?: string | null;
  /** the words and the label a move may set itself, as the person gave them; empty when the card's layout sets them */
  words?: string;
  label?: string;
  peak?: boolean;
  layers: Layer[];
};

export type Board = {
  id: string;
  /** the style card the board is made in */
  style?: string;
  name: string;
  handle: string;
  year: number;
  bpm: number;
  format: {width: number; height: number; fps: number; name?: string};
  system: System;
  beats: Beat[];
  /** the map, the stops' cards, the legs, the hook and the closer, solved in px of the format (scripts/board_drive.py) */
  route: unknown;
  /** the board's sound cues, `at` in musical beats from the film's start; its `stop` is where picture and sound stop together */
  sound?: {kind: string; at: number}[];
};

/** A generated clip placed on the card of the photograph it was made from: its frames `dir`/0001.jpg onward, from the film's frame `from`. */
export type Clip = {id: string; image: string; from: number; frames: number; dir: string};
export type FilmProps = {board: Board; clips?: Clip[]};
