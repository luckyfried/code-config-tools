export type Face = {
  family: string;
  file: string;
  weight: number;
  tracking: number;
  case: 'none' | 'uppercase' | 'lowercase';
  lineHeight: number;
};

export type Ease = {
  enter: [number, number, number, number];
  exit: [number, number, number, number];
  move: [number, number, number, number];
  spring: {damping: number; stiffness: number; mass: number};
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

export type BeatText = {kicker?: string; headline?: string; line?: string};

export type Clip = {
  id: string;
  file: string | null;
  /** the clip's frame count; its frames are file without .mp4, then /0001.jpg onward */
  frames?: number;
  image: string | null;
  status: 'generated' | 'their_reel' | 'substituted' | 'pending';
};

export type Transition = {preset: string; frames: number; direction?: string};

export type Beat = {
  id: string;
  kind: 'Opener' | 'ClipShot' | 'StatCard' | 'Mosaic' | 'KineticType' | 'PhotoLive' | 'Closer' | 'Diary';
  frames: number;
  transition?: Transition | null;
  treatment?: 'push' | 'parallax' | 'mask' | 'split';
  text?: BeatText;
  photos?: string[];
  clip?: Clip | null;
  data?: any;
  settle?: number;
};

/** The month the stories review: key "2026-09", name "September", short "Sept". */
export type Month = {key: string; name: string; short: string; year: number};

/** Where a card sits in the series: card n of the series' length, its role and its title. */
export type Series = {n: number; of: number; role: string; title: string};

export type Board = {
  id: string;
  name: string;
  handle: string;
  year: number;
  month: Month;
  format: {width: number; height: number; fps: number};
  system: System;
  /** the beats this render plays: the film's, or one card's */
  beats: Beat[];
  /** set when the render is a card of the series; the series mark sits at the top of the card */
  series?: Series | null;
};

export type FilmProps = {board: Board};
export type CardProps = {board: Board; beat: Beat; format: 'story'};
