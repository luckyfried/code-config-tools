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
  /** the film's field: dark, paper, or their lead color */
  field: 'dark' | 'paper' | 'lead';
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
    /** the guide cards: their ground, ink, accent and quiet ink */
    card: string;
    cardInk: string;
    cardAccent: string;
    cardMuted: string;
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
  kind: 'Opener' | 'ClipShot' | 'Reveal' | 'Swipe' | 'Poster';
  frames: number;
  transition?: Transition | null;
  treatment?: 'push' | 'parallax' | 'mask' | 'split';
  text?: BeatText;
  photos?: string[];
  clip?: Clip | null;
  data?: any;
  settle?: number;
};

/** One card of the brand guide, 1080x1350. Its fields depend on its kind; storyboard.py cards() writes them. */
export type GuideCardData = {
  n: number;
  id: string;
  kind: 'palette' | 'type' | 'compositions' | 'voice' | 'pillars' | 'cadence' | 'aspire' | 'stop' | 'statement' | 'week';
  title: string;
  [key: string]: any;
};

export type Board = {
  id: string;
  name: string;
  handle: string;
  format: {width: number; height: number; fps: number};
  system: System;
  beats: Beat[];
  /** the ten guide cards, in order */
  cards: GuideCardData[];
};

export type FilmProps = {board: Board};
/** One guide card as a still: the card's number in board.cards. */
export type CardProps = {board: Board; card: number};
