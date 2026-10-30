// The story film's plan, read from its board's `film` block (scripts/tones/drive.py): every post's card (its print at
// its station with its photograph and its label, the tile of the wall it lifts out of and drops back into, the
// camera's move into it, when the camera arrives and leaves, its date, their line and on a chapter their next line), the
// course across the wall with the closer's words for the span and the ask, the film's colors, the style card's finish,
// how its lines enter, and the timeline its moves, cuts and closer play on. All times are musical beats from the film's
// start; all places are px of the closer's frame (the wall), y down.
import {staticFile} from 'remotion';
import type {Look} from '../../system/moves';
import type {Timeline} from '../../system/moves/layer';
import type {CardFinish} from '../../system/three/Stage';
import type {Board} from '../../system/types';
import type {Pt} from '../../system/three/motion';

export type Box = [number, number, number, number];

/** One line of type: baseline start (x, y) in wall px, its size, face and weight, and where it is anchored. */
export type Line = {text: string; x: number; y: number; size: number; face?: string; weight?: number; tracking?: number; color?: string; anchor?: string; name?: string; at?: number};

export type Kind = 'hook' | 'ordinary' | 'milestone' | 'latest';

/** The camera's move into a card: its kind, how far it pulls back at its middle (a share of the frame's height), how
 * far it tips toward the way it travels up or down and banks and turns toward the way it travels across (radians), and
 * its ease (a cubic bezier: under 0 it winds back before it goes, over 1 it lands past its mark). */
export type Move = {kind: string; arc: number; pitch: number; bank: number; yaw: number; ease?: number[]};

export type Card = {
  id: string;
  kind: Kind;
  /** the photograph at the size a station shows it, and the small copy the wall shows */
  file: string;
  tileFile: string;
  /** width over height of the photograph */
  aspect: number;
  /** the print at its station (the paper, its label included), and its photograph there: [x0, y0, x1, y1] */
  rect: Box;
  photo: Box;
  /** the print's tile of the wall, and the photograph inside the tile's paper border */
  tile: Box;
  tilePhoto: Box;
  /** the windows of the photograph the print shows at its station and in its tile: [u0, v0, u1, v1], v up */
  uv0: Box;
  uv: Box;
  /** the photograph's focal point, as fractions of it (y down) */
  focal: Pt;
  /** how far the print stands off the wall while the camera is on it */
  lift: number;
  /** how far the camera pushes in through the hold */
  push: number;
  /** the camera's move into it (none into day one) */
  move: Move | null;
  arrive: number;
  leave: number;
  /** the camera's travel into it, and out of it (into the next card, or the closer's pull back) */
  travel: number;
  out: number;
  /** which of the three ways the print tips as it lifts out */
  entry: number;
  /** their line on the print's label, when its first letter starts in and when its last has landed */
  title: Line[];
  titleAt: number;
  land: number;
  date: Line;
  /** on day one, a milestone and the latest, their next line, and when it starts in */
  rest: Line[];
  restAt: number;
  station: {c: Pt; h: number; fov: number};
};

export type Plan = {
  W: number;
  H: number;
  pulse: number;
  colors: Record<string, string>;
  /** the style card's finish: its grain, vignette, bloom, cadence, letterbox bars and grade */
  finish: CardFinish;
  /** how a card's line enters, as the style card's photo layout says: rise, slam, type, fade or cut */
  enter: string;
  /** the beats the card's moves and cuts play on, the film's look as they read it, and the card's closer shape with
   * the beat it starts on */
  line: Timeline;
  look: Look;
  shape: {name: string; at: number};
  /** the beats a line's letters take, from the first entering to the last landed, and a card's lines to leave */
  letters: number;
  exit: number;
  /** enter: a letter or a print landing past its rest; move: the camera's travel when a move names no ease of its
   * own; drop: a print into its tile */
  ease: {enter: number[]; move: number[]; drop: number[]};
  /** the course of plain plaster across the wall that the closer's words are set on */
  course: Box;
  cards: Card[];
  closer: {at: number; move: number; still: number; end: number; frame: {c: Pt; h: number; fov: number}; lines: Line[]};
};


export const planOf = (board: Board): Plan => {
  const f = (board as any).film;
  const cl = f.closer;
  const cards: Card[] = f.cards.map((c: any, i: number) => ({
    id: c.id, kind: c.kind, file: c.file, tileFile: c.tile_file, aspect: c.aspect, rect: c.rect, photo: c.photo, tile: c.tile,
    tilePhoto: c.tile_photo, uv0: c.uv0, uv: c.uv, focal: c.focal, lift: c.lift, push: c.push, move: c.path ?? null,
    arrive: c.arrive, leave: c.leave, travel: c.travel, out: f.cards[i + 1]?.travel ?? cl.move, entry: c.entry,
    title: c.title.map((p: any) => ({...p})), titleAt: c.title_at, land: c.land,
    date: {...c.dateLine},
    rest: c.rest.map((p: any) => ({...p})), restAt: c.rest_at,
    station: c.station,
  }));
  const sys = board.system;
  const peak = cards[f.peak] ?? cards[cards.length - 1];
  const look = lookOf(board, f, peak?.file);
  return {
    W: f.W, H: f.H, pulse: f.pulse, colors: f.colors, finish: sys.finish, enter: sys.photo?.line?.enter ?? 'rise',
    line: f.timeline, look, shape: {name: f.shape, at: cl.shape},
    letters: f.letters, exit: f.exit, ease: f.ease, course: f.course, cards,
    closer: {at: cl.at, move: cl.move, still: cl.still, end: cl.end, frame: cl.frame, lines: cl.lines},
  };
};

/** A card's color, a role or a hex, as a hex. */
const toneOf = (colors: Record<string, string>, v: string) => {
  const hex = colors[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut, and closer: the frame, the card's colors, tones, grid, print and faces, the
 * board's own words, and the peak's photograph, the one a move that draws the photograph itself shows. */
export const lookOf = (board: Board, f: any, photo?: string): Look => {
  const sys = board.system;
  const colors = sys.colors as unknown as Record<string, string>;
  const g = sys.photo.grid;
  const pic = sys.photo.picture;
  const W: number = f.W, H: number = f.H;
  const m = g.margin * W;
  return {
    W, H, fps: board.format.fps, pulse: f.pulse, colors, display: sys.display.family, text: sys.text.family,
    italic: !!sys.display.italic, title: f.look.title, handle: f.look.handle, signoff: f.look.signoff,
    tone: {
      ground: toneOf(colors, sys.photo.ground), dip: sys.finish.dip === 'none' ? null : toneOf(colors, sys.finish.dip),
      matte: toneOf(colors, sys.finish.matte), light: toneOf(colors, sys.finish.light), pen: toneOf(colors, pic.penColor),
      rim: toneOf(colors, pic.rimColor), tape: toneOf(colors, pic.tapeColor),
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
    finished: sys.finish.words !== 'clean',
    photo: photo ? staticFile(photo) : undefined,
  };
};

/** Every line the film sets, for the fonts it loads. */
export const linesOf = (plan: Plan): Line[] => [
  ...plan.cards.flatMap((c) => [...c.title, c.date, ...c.rest]), ...plan.closer.lines,
];

/** The share of the camera's travel over which a print lifts out of its tile, and over which it drops back. */
export const RISE = 0.6;
export const DROP = 0.6;

/** A print's timings in beats, [start, length]: its lift out of its tile over the last of the camera's move to it
 * (day one's over the camera's dive from the whole wall onto it), and its drop back into its tile over the first of the
 * move out of it, so every move shows one print going home and the next coming out of the wall. Until its lift starts
 * a print stands dim in its tile. */
export const timesOf = (c: Card) => ({
  rise: c.kind === 'hook' ? [0.25 * c.arrive, 0.75 * c.arrive] : [c.arrive - RISE * c.travel, RISE * c.travel],
  drop: [c.leave, DROP * c.out],
});

/** A wall point in world space at depth z. */
export const world = (plan: Plan, p: Pt, z = 0): [number, number, number] => [p[0] - plan.W / 2, plan.H / 2 - p[1], z];
