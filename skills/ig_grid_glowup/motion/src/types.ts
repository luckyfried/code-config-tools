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

/** The three grid directions: one warm tonal grade; rows blocked by color; photo and type alternating. */
export type Look = 'tonal' | 'blocks' | 'alternate';

/** One of the next nine posts, n 1 to 9 in posting order (n 9 is posted last and sits top left). */
export type Post = {
  n: number;
  kind: 'photo' | 'type' | 'color';
  /** a build/public path: graded/<name>.jpg for their photo, stills/<name>.jpg for a generated stand-in */
  photo?: string | null;
  still?: boolean;
  focal?: string;
  /** blocks: the row's color the photo leans toward, and a color tile's fill */
  tint?: string;
  /** type and color posts: the fill and the ink */
  bg?: string;
  ink?: string;
  /** tonal: a paper matte around the photo */
  matte?: boolean;
  text?: BeatText;
  caption?: string;
};

/** A cell of their real grid, newest first. */
export type Cell = {pos: number; photo: string | null; kind: 'post' | 'reel'};

export type Profile = {name: string; bio: string; posts: number; followers: number; following: number; avatar: string | null};

/** A finding drawn over the real grid in the before shot. */
export type Callout = {positions: number[]; label: string};

export type Transition = {preset: string; frames: number; direction?: string};

export type Beat = {
  id: string;
  kind: 'Opener' | 'ClipShot' | 'Feed';
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
  look: Look;
  posts: Post[];
  grid: Cell[];
  profile: Profile;
};

export type FilmProps = {board: Board};
export type PostProps = {board: Board; post: Post};
export type SheetProps = {board: Board; rows?: number};
