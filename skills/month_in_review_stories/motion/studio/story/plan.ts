// A story card as the board builder wrote it (scripts/compose/stories.py): every place in frame px (1080x1920, y down),
// every time a beat of the card from its first frame. A card is its shots (the camera's framings) and what stands in
// front of the camera: the moment's photograph as a band, the line, plates sized to the words and lines of
// type. A value that changes over the card is a track.
import {clamp01} from '../../system/three/motion';

export type Box = [number, number, number, number];
/** [beat, value, ease]: the ease is how the value travels from the point before */
export type Track = [number, number, 'settle' | 'smooth'][];

export type View = {c: [number, number]; h: number; yaw: number; pitch: number; roll: number};
export type Shot = {beats: number; view: View; to?: View; push: number; arc?: number; reveals: string};

export type Band = {
  file: string | null;
  rect: Box;
  /** the whole photograph laid over the frame, [x, y, w, h] frame px */
  place: [number, number, number, number];
  enter?: {at: number; len: number; from: 'left' | 'right'};
};

export type Rule = {x0: number; x1: number; y: Track; at: number; color: string};
export type Strip = {rect: Box; at: number; len: number; out?: number; z?: number};

export type Line = {
  text: string; x: number; y: number; size: number; face?: string; weight?: number; color?: string; anchor?: string;
  at: number; out?: number; shadow?: number; z?: number;
  /** the card's tracking for the line's face, em */
  tracking?: number;
  /** the font file the line is set in (the look's family) */
  file?: string;
  /** a count counts up from zero, from beat `at` over `beats` */
  tally?: {at: number; beats: number};
};
export type Burst = {at: number; x0: number; x1: number; y: number; big: boolean};

export type Card = {
  id: string;
  frames: number;
  idea: string;
  shots: Shot[];
  /** the beat the card's still is taken at */
  still: number;
  /** the camera's move into a shot: from move[0] beats before the shot's first beat to move[1] after it */
  move: [number, number];
  /** how far the camera banks and looks ahead on its moves: 0 where the photographs fill the frame exactly */
  bank: number;
  bands: Band[];
  rules: Rule[];
  strips: Strip[];
  lines: Line[];
  bursts: Burst[];
};

export type Colors = Record<string, string>;
export type Series = {bpm: number; format: {width: number; height: number; fps: number}; system: {colors: Colors}; beats: Card[]};

const ease = (name: string, u: number) => {
  u = clamp01(u);
  return name === 'settle' ? 1 - (1 - u) * (1 - u) : u * u * (3 - 2 * u);
};

/** A track's value at beat `t`; `fallback` when the track is empty. */
export const at = (tr: Track | undefined, t: number, fallback = 0) => {
  if (!tr || !tr.length) return fallback;
  if (t <= tr[0][0]) return tr[0][1];
  for (let i = 1; i < tr.length; i++) {
    const [a, va] = tr[i - 1];
    const [b, vb, e] = tr[i];
    if (t <= b) return va + (vb - va) * ease(e, (t - a) / Math.max(1e-6, b - a));
  }
  return tr[tr.length - 1][1];
};

export const startsOf = (c: Card) => {
  let a = 0;
  return c.shots.map((s) => {
    const x = a;
    a += s.beats;
    return x;
  });
};

/** The framing a shot's hold ends on: its `to`, or its view pushed in by `push`. */
export const heldOf = (s: Shot): View => s.to ?? {...s.view, h: s.view.h * (1 - s.push)};

export const pulseOf = (bpm: number, fps: number) => (fps * 60) / bpm;

/** The brightest of the palette's colors: the scene's key light. */
export const brightest = (colors: Colors) => Object.values(colors).reduce((a, b) => (luma(b) > luma(a) ? b : a));
const luma = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
};
export const colorOf = (colors: Colors, name?: string) => colors[name ?? 'ink'] ?? name ?? colors.ink;
