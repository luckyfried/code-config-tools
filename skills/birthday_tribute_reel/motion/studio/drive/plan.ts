// The year's plan, read from its board: every moment's card, where it lands on the closer's wall, when it arrives, when
// it lands and when it leaves, its name and its words, and the closer's giant age, its last figure and the wish.
// All times are musical beats from the film's start; all places are px of the closer's frame (the wall), y down.
import {staticFile} from 'remotion';
import type {Board, Finish, PhotoLayout} from '../../system/types';
import type {Pt} from '../../system/three/motion';
import type {Look} from '../../system/moves/types';

export type Box = [number, number, number, number];

/** One line of type as compose.py sets it: px baseline at (x, y), turned `rotate` degrees clockwise about `pivot`, in `file`. */
export type Line = {
  text: string;
  x: number;
  y: number;
  size: number;
  file: string;
  tracking?: number;
  color?: string;
  rotate?: number;
  pivot?: Pt;
  anchor?: string;
  name?: string;
};

/** A card's frame px mapped onto the wall: scaled by `s` about the origin, then moved by `o`. */
export type Xf = {s: number; o: Pt};
export const onWall = (T: Xf, p: Pt): Pt => [T.o[0] + T.s * p[0], T.o[1] + T.s * p[1]];

/** Where a line's baseline starts and the angle it runs at, in px of its frame: its start turned about its pivot. */
export const baseline = (ln: Line): {at: Pt; deg: number} => {
  const deg = ln.rotate ?? 0;
  const [cx, cy] = ln.pivot ?? [ln.x, ln.y];
  const a = (deg * Math.PI) / 180;
  const dx = ln.x - cx, dy = ln.y - cy;
  return {at: [cx + dx * Math.cos(a) - dy * Math.sin(a), cy + dx * Math.sin(a) + dy * Math.cos(a)], deg};
};

/** A line placed on the wall: baseline start, angle (degrees clockwise), size, all in wall px. */
export type Placed = {at: Pt; deg: number; size: number};
export const placeOnWall = (T: Xf, ln: Line): Placed => {
  const b = baseline(ln);
  return {at: onWall(T, b.at), deg: b.deg, size: ln.size * T.s};
};

export type Card = {
  key: string;
  post: string;
  hook: boolean;
  file: string;
  /** the photograph's line in the card's frame, the one the name stands on or hangs from: y at its left side and at its
   * right side */
  line: Pt;
  field: string;
  /** the photograph laid whole in the card's frame */
  place: Box;
  /** the photograph's subject in the card's frame (left, top, right, bottom), the point a hold arcs about */
  subject: Box;
  T: Xf;
  /** the card's cell on the closer's wall (top left, top right, bottom right, bottom left) */
  slot: Pt[];
  arrive: number;
  leave: number;
  /** when the card lands on its lift and its name rises out of its line */
  cut: number;
  /** the name on the line, a row or two: the age on the hook, the moment's name on every other */
  head: Line[];
  /** the card's words: the rest of its caption or the lines the two traded under it (the hook's day and tag too) */
  lines: Line[];
  /** the type's colour: the paper's over shade, or ink over a veil of the paper's light */
  type: 'paper' | 'ink';
  /** how much light the photograph under the type loses (paper type) or is given (ink type), 0 to 1 */
  shade: number;
  /** the left and right of the type in the card's frame, the span of the picture whose light the shade changes */
  typeX: Pt;
  /** which side of the line the type is set on: over it (the subject under) or under it (the subject over) */
  side: 'over' | 'under';
  /** how the card arrives on its line, chosen by the board from its photograph: fall (the hook), hinge, slide or rise */
  entry: 'fall' | 'hinge' | 'slide' | 'rise';
};

/** One beat of the board as the moves see it: its form, when it starts and ends, the move and the cut into it the board
 * chose from its content, and its label. */
export type Step = {id: string; form: string; at: number; end: number; move?: string; transition?: string | null; words: string; label: string; peak: boolean};

export type Plan = {
  W: number;
  H: number;
  pulse: number;
  colors: Record<string, string>;
  ease: {enter: number[]; move: number[]};
  cards: Card[];
  steps: Step[];
  fps: number;
  /** the card's finish: its grade, grain, bloom, cadence and letterbox bars */
  finish: Finish;
  /** the card's photo beat: how each print is dressed (its margin, rim, tilt and tape), the ground it is pasted on, and
   * how dark the picture is shaded under the type */
  photo: PhotoLayout;
  /** the card's closer, and the faces and words it is set in */
  closerShape: string;
  faces: {display: string; text: string; italic: boolean};
  wish: {title: string; from: string};
  /** when the closer begins, the giant age cut out of the paper and its last figure, the wish, the top and bottom of
   * the core of each band under the wish's lines (wall px), and `still`: where the picture and the sound stop together */
  closer: {at: number; big: Line; last: Line; lines: Line[]; bands: number[][]; still: number};
  end: number;
};

/** Beats from a card's arrival to its landing on its lift, where its name rises and its hit falls, as wall.py LIFT and
 * HOOK_LIFT. */
const LIFT = 0.25;
const HOOK_LIFT = 0.3;

export const planOf = (board: Board): Plan => {
  const {width: W, height: H, fps} = board.format;
  const pulse = (fps * 60) / board.bpm;
  const starts: Record<string, number> = {};
  let f = 0;
  for (const b of board.beats) {
    starts[b.id] = f / pulse;
    f += b.frames ?? Math.round(b.bars * 4 * pulse);
  }
  const end = f / pulse;
  const order = board.beats.map((b) => b.id);
  const nextStart = (id: string) => {
    const i = order.indexOf(id);
    return i + 1 < order.length ? starts[order[i + 1]] : end;
  };
  const film = board.film;
  const cards: Card[] = film.cards.map((c: any) => {
    const arrive = starts[c.key];
    return {
      key: c.key, post: c.post, hook: c.hook, file: c.file, line: c.line, field: c.field ?? 'paper', place: c.place, subject: c.subject ?? [W * 0.3, H * 0.3, W * 0.7, H * 0.7], T: c.T, slot: c.slot,
      arrive, leave: nextStart(c.key), cut: arrive + (c.hook ? HOOK_LIFT : LIFT), head: c.head, lines: c.lines, type: c.type ?? 'paper', shade: c.shade ?? 0.4, typeX: c.type_x ?? [0, W], side: c.side ?? 'over',
      entry: c.entry ?? (c.hook ? 'fall' : 'rise'),
    };
  });
  const C = starts.closer ?? end;
  const steps: Step[] = board.beats.map((b) => ({id: b.id, form: b.form ?? 'photo', at: starts[b.id], end: nextStart(b.id), move: b.move,
    transition: b.transition, words: '', label: b.label ?? '', peak: Boolean(b.peak)}));
  const lines = film.closer.lines as Line[];
  const named = (n: string) => lines.find((l) => l.name === n)?.text ?? '';
  return {
    W, H, pulse, colors: board.system.colors as unknown as Record<string, string>,
    ease: {enter: board.system.ease.enter, move: board.system.ease.move},
    cards, steps, fps, finish: board.system.finish, photo: board.system.photo, closerShape: board.system.closer,
    faces: {display: board.system.display.family, text: board.system.text.family, italic: Boolean(board.system.display.italic)},
    wish: {title: named('title'), from: lines.filter((l) => l.name?.startsWith('wish-')).map((l) => l.text).pop() ?? ''},
    closer: {at: C, big: film.closer.big, last: film.closer.last, lines: film.closer.lines, bands: film.closer.bands, still: board.sound?.find((s) => s.kind === 'stop')?.at ?? end},
    end,
  };
};

/** A color the card names: one of the board's roles, or a hex. */
export const paint = (plan: Plan, color: string) => plan.colors[color] ?? color;

/** A card's color, a role or a hex, as a hex. */
const toneOf = (plan: Plan, v: string) => {
  const hex = plan.colors[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut, and closer: the frame, the card's colors, tones, grid and faces, the print the
 * card dresses a photograph as, the occasion's photograph, and the board's own words: the giant figure (the age, the
 * years, or the name) is the closer's title where its shape sets one, the wish is the closing line, and its sender the
 * line under it. */
export const lookOf = (plan: Plan): Look => {
  const g = plan.photo.grid;
  const pic = plan.photo.picture;
  const m = g.margin * plan.W;
  const hook = plan.cards.find((c) => c.hook) ?? plan.cards[0];
  return {
    W: plan.W, H: plan.H, fps: plan.fps, pulse: plan.pulse, colors: plan.colors,
    display: plan.faces.display, text: plan.faces.text, italic: plan.faces.italic,
    title: plan.closer.big?.text ?? '', handle: plan.wish.from, signoff: plan.wish.title,
    tone: {
      ground: toneOf(plan, plan.photo.ground), dip: plan.finish.dip === 'none' ? null : toneOf(plan, plan.finish.dip),
      matte: toneOf(plan, plan.finish.matte), light: toneOf(plan, plan.finish.light), pen: toneOf(plan, pic.penColor),
      rim: toneOf(plan, pic.rimColor), tape: toneOf(plan, pic.tapeColor),
    },
    grid: {
      m, rules: g.rules,
      cols: Array.from({length: g.cols + 1}, (_, i) => m + (i * (plan.W - 2 * m)) / g.cols),
      rows: Array.from({length: g.rows + 1}, (_, i) => m + (i * (plan.H - 2 * m)) / g.rows),
    },
    finished: plan.finish.words !== 'clean',
    photo: hook ? staticFile(hook.file) : undefined,
    print: {
      box: [Math.max(0, pic.box[0]) * plan.W, Math.max(0, pic.box[1]) * plan.H,
        (Math.min(1, pic.box[0] + pic.box[2]) - Math.max(0, pic.box[0])) * plan.W, (Math.min(1, pic.box[1] + pic.box[3]) - Math.max(0, pic.box[1])) * plan.H],
      rim: pic.rim * plan.W, tilt: pic.tilt, tape: pic.tape,
    },
  };
};
