// The board as the film reads it: the frame, the type area the card's safe area leaves, the beats on the music's
// timeline with what each hands its move, the look every move and closer is drawn in, and for each stop beat where its
// picture stands and how the camera walks it, from where the person stood toward what the photograph looks at.
import {staticFile} from 'remotion';
import {bezier, clamp01, lerp} from '../system/three/motion';
import {cutOf, type BeatOn, type Look} from '../system/moves';
import type {Timeline} from '../system/moves/layer';
import type {Beat, Board, Stop, System} from '../system/types';

/** The moves that set a beat's label or words themselves: the film's own words leave that part to them. A doodle on a
 * photograph draws round the print and sets no word, so the film sets the place's name under it. */
export const LABELS = new Set(['date-stamp', 'polaroid-drop', 'sticker-pop']);
export const LINES = new Set(['long-fade-title']);

export type Shot = {
  beat: Beat;
  index: number;
  stop: Stop;
  /** where the picture stands, frame px [x0, y0, x1, y1], and whether that is the whole frame */
  box: [number, number, number, number];
  full: boolean;
  /** the box the stop's label and line are set in, frame px [x0, y0, x1, y1] */
  line: [number, number, number, number];
  /** the beats the picture holds still in its place: from when it has landed to when its words start to leave */
  held: [number, number];
  /** the card's print dress: rim (px), tilt (degrees), tape strips */
  rim: number;
  tilt: number;
  tape: number;
};

export type Plan = {
  W: number;
  H: number;
  fps: number;
  pulse: number;
  system: System;
  /** the type area: the frame less the format's safe margins, [x0, y0, x1, y1] */
  area: [number, number, number, number];
  line: Timeline;
  look: Look;
  shots: Shot[];
  title: string;
  kicker: string;
  closer: {name: string; at: number; still: number};
  move: (u: number) => number;
  enter: (u: number) => number;
  exit: (u: number) => number;
};

const SHARE = (a: number, b: number, s: number) => a + (b - a) * s;

/** The card's photo layout for a stop: a photograph wider than it is tall on a tall frame takes the card's landscape
 * picture box and line box, so it fills the frame's foot instead of leaving bare page under it. */
export const layoutOf = (sys: System, stop: Stop | undefined, W: number, H: number) => {
  const lay = sys.photo;
  const wide = Boolean(stop && stop.aspect < 1 && H > W && lay.landscape);
  return {box: wide ? lay.landscape.box : lay.picture.box, line: wide ? lay.landscape.line : lay.line.box};
};

/** A box of shares of `of` ([x, y, w, h]) in frame px, [x0, y0, x1, y1]. */
const within = (of: [number, number, number, number], [x, y, w, h]: number[]): [number, number, number, number] => {
  const [a0, b0, a1, b1] = of;
  return [a0 + x * (a1 - a0), b0 + y * (b1 - b0), a0 + (x + w) * (a1 - a0), b0 + (y + h) * (b1 - b0)];
};

/** When a beat's words start to leave: before the cut out of it has played its first half. */
export const leaveOf = (beats: Beat[], i: number, end: number) => {
  const next = cutOf(beats[i + 1]?.transition);
  return end - Math.max(0.5, next ? next.beats / 2 : 0);
};

export const planOf = (board: Board): Plan => {
  const {width: W, height: H, fps} = board.format;
  const sys = board.system;
  const pulse = board.beats[0]?.pulse ?? (fps * 60) / board.bpm;
  const safe = sys.safe[board.format.name || 'reel'] ?? sys.safe.reel;
  const area: [number, number, number, number] = [safe.left, safe.top, W - safe.right, H - safe.bottom];
  const r = board.route;
  const shots: Shot[] = [];
  const beats: BeatOn[] = board.beats.map((b, i) => {
    const at = b.at ?? 0, end = b.end ?? at + 4 * b.bars;
    const title = b.form === 'title';
    // the hook hands a labelling move the trip's name, a stop hands it its place (or its date, for a dated move); a
    // move that sets the line is handed the line
    const label = !b.move || !LABELS.has(b.move) ? '' : title && b.move !== 'date-stamp' ? r.title : b.label;
    const words = b.move && LINES.has(b.move) ? b.words : '';
    if (b.form === 'closer') return {id: b.id, form: b.form, at, end, move: b.move ?? undefined, transition: b.transition, words, label, peak: b.peak};
    const pic = sys.photo.picture;
    const stop = r.stops[b.stops[0]];
    const lay = layoutOf(sys, title ? undefined : stop, W, H);
    const boxed = !title && pic.show;
    const [bx, by, bw, bh] = boxed ? lay.box : [0, 0, 1, 1];
    const box: [number, number, number, number] = [bx * W, by * H, (bx + bw) * W, (by + bh) * H];
    const full = !boxed || (bx === 0 && by === 0 && bw === 1 && bh === 1);
    // a pasted print lands over its first beat and a half; a photograph over the whole frame is in place from its cut
    const held: [number, number] = [full ? at : at + 1.4, leaveOf(board.beats, i, end) - 0.6];
    const shot: Shot = {beat: {...b, at, end}, index: i, stop, box, full, line: within(area, lay.line), held,
      rim: full ? 0 : pic.rim * W, tilt: full ? 0 : pic.tilt, tape: full ? 0 : pic.tape};
    shots.push(shot);
    // a stop's move is handed where its photograph stands, where its words stand, and the beats it holds still, so a
    // mark drawn on the photograph sits on it and is gone before the cut out
    return {id: b.id, form: b.form, at, end, move: b.move ?? undefined, transition: b.transition, words, label, peak: b.peak,
      ...(title ? {} : {box, type: shot.line, held})};
  });
  const plan = {W, H, fps, pulse, system: sys, area, line: {beats, cuts: beats.map((b) => b.at)}, shots, title: r.title, kicker: r.kicker,
    closer: {name: sys.closer, at: r.closer.at, still: r.closer.still},
    move: bezier(sys.ease.move), enter: bezier(sys.ease.enter), exit: bezier(sys.ease.exit)};
  return {...plan, look: lookOf(board, plan.shots)};
};

/** A card's color, a role or a hex, as a hex. */
const toneOf = (colors: Record<string, string>, v: string) => {
  const hex = colors[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut, and closer: the frame, the card's colors, tones, grid, print and faces, the trip's
 * own words, and the hook's photograph. */
const lookOf = (board: Board, shots: Shot[]): Look => {
  const {width: W, height: H, fps} = board.format;
  const sys = board.system, r = board.route;
  const pulse = board.beats[0]?.pulse ?? (fps * 60) / board.bpm;
  const colors = Object.fromEntries(Object.entries(sys.colors).filter(([k]) => k !== 'swatches')) as Record<string, string>;
  const f = sys.finish, pic = sys.photo.picture, g = sys.photo.grid;
  const m = g.margin * W;
  return {
    W, H, fps, pulse, colors, display: sys.display.family, text: sys.text.family, italic: Boolean(sys.display.italic),
    title: r.title, handle: r.handle, signoff: r.signoff,
    tone: {
      ground: toneOf(colors, sys.photo.ground), dip: f.dip === 'none' ? null : toneOf(colors, f.dip), matte: toneOf(colors, f.matte),
      light: toneOf(colors, f.light), pen: toneOf(colors, pic.penColor), rim: toneOf(colors, pic.rimColor), tape: toneOf(colors, pic.tapeColor),
    },
    grid: {
      m, rules: g.rules,
      cols: Array.from({length: g.cols + 1}, (_, i) => m + (i * (W - 2 * m)) / g.cols),
      rows: Array.from({length: g.rows + 1}, (_, i) => m + (i * (H - 2 * m)) / g.rows),
    },
    print: {
      box: [Math.max(0, pic.box[0]) * W, Math.max(0, pic.box[1]) * H,
        (Math.min(1, pic.box[0] + pic.box[2]) - Math.max(0, pic.box[0])) * W, (Math.min(1, pic.box[1] + pic.box[3]) - Math.max(0, pic.box[1])) * H],
      rim: pic.rim * W, tilt: pic.tilt, tape: pic.tape,
    },
    finished: f.words !== 'clean',
    photo: shots[0] ? staticFile(shots[0].stop.photo) : undefined,
  };
};

/** The stop beat the film is on at `t` (the last one before the closer holds through it). */
export const shotAt = (plan: Plan, t: number): Shot | undefined => {
  let on: Shot | undefined;
  for (const s of plan.shots) if (t >= (s.beat.at ?? 0) || !on) on = s;
  return on;
};

/** A point between two, by `u`. */
export const toward = (a: [number, number], b: [number, number], u: number): [number, number] => [SHARE(a[0], b[0], u), SHARE(a[1], b[1], u)];

/**
 * The part of the photograph the picture's box shows at `t`: its middle (photograph widths across, down), its width and
 * height in photograph widths, and its turn. The box shows the photograph covered edge to edge; over the beat the camera
 * settles in from the cover toward what the photograph looks at, and the move's nudge turns and shifts it; whatever the
 * nudge asks, the part stays inside the photograph, so no edge ever shows.
 */
export const cropAt = (plan: Plan, shot: Shot, t: number, nudge: {scale?: number; dx?: number; dy?: number; roll?: number}) => {
  const {stop, box} = shot;
  const at = shot.beat.at ?? 0, end = shot.beat.end ?? at + 4;
  const u = clamp01((t - at) / Math.max(0.5, end - at));
  const A = stop.aspect;
  const r = (box[3] - box[1]) / (box[2] - box[0]);
  const most = Math.min(1, A / r);
  const e = plan.move(u);
  // a peak opens wide and pushes further; every other beat settles in a little
  const k = clamp01(lerp(shot.beat.peak ? 1 : 0.96, shot.beat.peak ? 0.8 : 0.86, e) * (nudge.scale ?? 1));
  let cw = most * k, ch = cw * r;
  const roll = nudge.roll ?? 0;
  const c = Math.abs(Math.cos(roll)), s = Math.abs(Math.sin(roll));
  const fit = Math.min(1, 1 / (cw * c + ch * s), A / (cw * s + ch * c));
  cw *= fit;
  ch *= fit;
  const bw = cw * c + ch * s, bh = cw * s + ch * c;
  const near: [number, number] = [stop.near[0], stop.near[1] * A], far: [number, number] = [stop.far[0], stop.far[1] * A];
  let [x, y] = toward(near, far, 0.35 + 0.5 * e);
  x += (nudge.dx ?? 0) * ch;
  y += (nudge.dy ?? 0) * ch;
  x = Math.min(1 - bw / 2, Math.max(bw / 2, x));
  y = Math.min(A - bh / 2, Math.max(bh / 2, y));
  return {x, y, cw, ch, roll, A};
};
