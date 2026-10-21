export type Face = {
  family: string;
  file: string;
  weight: number;
  tracking: number;
  case: 'none' | 'uppercase' | 'lowercase';
  lineHeight: number;
  /** variable-font axes set on the face, such as {"wdth": 68} for a condensed cut or {"opsz": 144, "SOFT": 100} */
  axes?: Record<string, number>;
};

export type Ease = {
  enter: [number, number, number, number];
  exit: [number, number, number, number];
  move: [number, number, number, number];
  spring: {damping: number; stiffness: number; mass: number};
  /** the overshooting spring of a thing landing on a beat */
  hit: {damping: number; stiffness: number; mass: number};
  stagger: number;
};

export type Safe = {top: number; bottom: number; left: number; right: number};

export type System = {
  direction: 'editorial' | 'kinetic' | 'documentary';
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
  texture: {grain: number; vignette: number; leaks: boolean};
  ease: Ease;
  safe: Record<string, Safe>;
};

export type Clip = {
  id: string;
  file: string | null;
  /** the clip's frame count; its frames are file without .mp4, then /0001.jpg onward */
  frames?: number;
  image: string | null;
  status: 'generated' | 'their_reel' | 'substituted' | 'pending';
};

/** The designed moves of a cut; `cut` is a plain hard cut on the downbeat. */
export type Preset = 'cut' | 'whip' | 'match' | 'maskWipe' | 'zoomThrough' | 'flash' | 'dissolve' | 'dip';

/** `frames` is the length of the move on each side of the cut; `origin` is where a maskWipe or zoomThrough centres, in fractions of the frame. */
export type Transition = {preset: Preset; frames?: number; direction?: 'left' | 'right' | 'up' | 'down'; origin?: [number, number]};

/** A palette key or a hex color. */
export type Color = 'bg' | 'ink' | 'accent' | 'accent2' | 'muted' | 'paper' | string;

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
  /** length in bars of the track: 1, 2 or 4 */
  bars: number;
  /** frames, set by storyboard.py snap from the track's downbeats */
  frames?: number;
  /** frames per musical beat, set by snap from the track's tempo */
  pulse?: number;
  transition?: Transition | null;
  layers: Layer[];
  /** musical beats inside the beat where a layer lands (a slam, a counter landing); the hits layer of the sound sits on them */
  hits?: number[];
  /** the beat's camera over its ground, picture and shape layers: a push of 7 percent scale per bar (default), a drift of 9 percent of the width per bar, a breathe of 2.5 percent scale per bar, or none */
  camera?: 'push' | 'drift' | 'breathe' | 'none';
  /** the frame from which a type block counts as settled for the safe-area check (cards use 0) */
  settle?: number;
};

export type Board = {
  id: string;
  name: string;
  handle: string;
  year: number;
  bpm: number;
  tone: 'drive' | 'film' | 'calm';
  format: {width: number; height: number; fps: number};
  system: System;
  beats: Beat[];
  cards?: Beat[];
  stories?: Beat[];
  /** the drive board's sound cues, `at` in musical beats from the film's start; its `stop` is where picture and sound stop together */
  sound?: {kind: string; at: number}[];
};

/** A generated clip placed on the card of the photograph it was made from: its frames `dir`/0001.jpg onward, from the film's frame `from`. */
export type Clip = {id: string; image: string; from: number; frames: number; dir: string};
export type FilmProps = {board: Board; clips?: Clip[]};
export type CardProps = {board: Board; beat: Beat; format: 'carousel' | 'story'; index: number; total: number};
