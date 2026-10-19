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
  kind: 'Opener' | 'ClipShot' | 'Dated' | 'Split' | 'Chapter';
  frames: number;
  transition?: Transition | null;
  treatment?: 'push' | 'parallax' | 'mask' | 'split';
  text?: BeatText;
  photos?: string[];
  clip?: Clip | null;
  data?: any;
  settle?: number;
  /** the subject post a photo beat shows, and its date */
  post?: string;
  /** a photo beat's date, or a then/now beat's two dates */
  at?: string | string[];
  /** a then/now beat's two posts: the first and the latest */
  posts?: string[];
};

export type Span = {first: string; latest: string; months: number; days: number; label: string; from: string; to: string};

export type Board = {
  id: string;
  name: string;
  handle: string;
  subject: string;
  span: Span;
  format: {width: number; height: number; fps: number};
  system: System;
  beats: Beat[];
  /** the then/now card (1080x1350): the first and the latest photo side by side with the span */
  card?: Beat;
};

export type FilmProps = {board: Board};
export type CardProps = {board: Board; beat: Beat; format: 'portrait'};
