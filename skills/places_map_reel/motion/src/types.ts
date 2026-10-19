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
  /** the map's colors: sea, land, coastline, the route and its pins, the labels and the halo behind them */
  map: {sea: string; land: string; coast: string; route: string; pin: string; label: string; halo: string};
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

/** A camera on the map: center x, center y and the frame's width, in world units (web mercator, 0 to 1000). */
export type Cam = [number, number, number];

export type MapPin = {id: string; name: string; x: number; y: number; far: boolean; home: boolean; rows: number; km_from_home: number | null};

export type Leg = {from: string; to: string; km: number; far: boolean; arc: [number, number][]};

/** The places of the year on one map: the land file, a pin per place, a curve per leg, the route's order. */
export type MapData = {land: string; pins: MapPin[]; legs: Leg[]; route: string[]};

/** One format's poster layout, in px: the map rect, its camera, the inset for far places, each label's side. */
export type MapLayout = {
  rect: [number, number, number, number];
  cam: Cam;
  inset: {rect: [number, number, number, number]; cam: Cam; ids: string[]} | null;
  labels: Record<string, string>;
  size: number;
};

/** One place's stamp in the passport: its shape and tilt, its photos and its dates. */
export type StampData = {
  id: string;
  name: string;
  shape: 'circle' | 'rect' | 'octagon' | 'oval';
  tilt: number;
  photos: string[];
  country?: string;
  when?: string;
  visits?: number;
};

export type Transition = {preset: string; frames: number; direction?: string};

export type Beat = {
  id: string;
  kind: 'Opener' | 'ClipShot' | 'MapJourney' | 'Stamp' | 'DayNight' | 'Poster';
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
  map: MapData;
  count?: number;
  total_km?: number;
  /** the map poster (1080x1350) */
  poster?: Beat;
};

export type FilmProps = {board: Board};
export type CardProps = {board: Board; beat: Beat; format: 'poster' | 'reel'};
