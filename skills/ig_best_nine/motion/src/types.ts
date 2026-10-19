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

/** One of the nine: rank 1 is the most liked. */
export type Tile = {
  rank: number;
  photo: string;
  likes?: number | null;
  comments?: number | null;
  label?: string;
  caption?: string;
  kind?: string;
  clip?: Clip | null;
};

export type Transition = {preset: string; frames: number; direction?: string};

export type Beat = {
  id: string;
  kind: 'Opener' | 'ClipShot' | 'Countdown' | 'Grid';
  frames: number;
  transition?: Transition | null;
  treatment?: 'push' | 'parallax' | 'mask' | 'split';
  text?: BeatText;
  photos?: string[];
  clip?: Clip | null;
  data?: any;
  settle?: number;
};

export type Board = {
  id: string;
  name: string;
  handle: string;
  year: number;
  format: {width: number; height: number; fps: number};
  system: System;
  beats: Beat[];
  /** the best-nine image (1080x1080) */
  wall?: Beat;
  /** the story card (1080x1920) */
  story?: Beat;
};

export type FilmProps = {board: Board};
export type CardProps = {board: Board; beat: Beat; format: 'square' | 'story'};
