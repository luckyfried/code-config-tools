// The places film's plan, read from its board: the map, every stop's card (where its photograph stands in the frame by
// the style card's layout, the words the layout sets, the pin it opens out of and the print it folds into), the legs
// between the stops, the hook's title, and the closer. All times are musical beats from the film's start; all places
// are px of the closer's frame (the wall), y down.
import {staticFile} from 'remotion';
import type {Look} from '../../system/moves/types';
import {bezier, span, type Pt} from '../../system/three/motion';
import type {Board, Finish, PhotoLayout} from '../../system/types';

export type Box = [number, number, number, number];

/** One line of type as the board sets it: px baseline at (x, y), turned `rotate` degrees clockwise about `pivot`. */
export type Line = {
  text: string;
  x: number;
  y: number;
  size: number;
  /** the font file, from the style card's faces */
  file: string;
  tracking?: number;
  color?: string;
  rotate?: number;
  pivot?: Pt;
  anchor?: 'start' | 'middle' | 'end';
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

export type Entry = 'pin' | 'polaroid-drop' | 'tape-slap' | 'sticker-pop' | 'paper-slide';

type CardIn = {
  id: string;
  i: number;
  kind: 'hook' | 'peak' | 'new' | 'quick';
  place: string;
  name: string;
  n: number;
  file: string;
  /** the photograph's rectangle in the card's frame, [x, y, w, h], and the part of the frame it covers, [x0, y0, x1, y1] */
  photo: Box;
  box: Box;
  pin: Pt;
  /** where the photograph rests on the map once the camera moves on: the center of its print and its side, wall px */
  slot: Pt;
  size: number;
  crop: [number, number, number, number];
  s: number;
  o: Pt;
  lines: Line[];
  cut: number;
  go: number;
  /** the person's line about the visit, or null for a wordless one */
  said: string | null;
  far: boolean;
  /** reached heading west: the photograph drifts the way the dot came */
  west?: boolean;
  /** the camera's travel out of the stop: between two near places a rise over the map or a lift onto the leg, in turn;
   * across the water a leap; into the closer the closer's move */
  travel: 'rise' | 'lift' | 'leap' | 'closer';
  /** how the photograph comes onto its page: out of its pin, or by one of the style card's own moves (dropped from
   * above, slapped down, popped out from its middle, slid in from the side) */
  entry?: Entry;
  /** the photograph's focus in frame px, the point it pushes toward while its place holds */
  focus: Pt;
};

export type Card = CardIn & {
  T: Xf;
  /** when the camera reaches the stop, when the next stop's beat begins, when the stop's words come up */
  arrive: number;
  leave: number;
  cutAt: number;
  /** when the camera leaves for the next stop and when it lands there */
  goAt: number;
  landAt: number;
  /** when the photograph begins to open out of its pin and how many beats it takes: on a move from a near place it
   * opens while the camera travels, so the print it leaves and the photograph it reaches share the move */
  openAt: number;
  openLen: number;
  /** when it begins to fold onto its print and how many beats it takes */
  foldAt: number;
  foldLen: number;
};

export type Leg = {from: number; to: number; far: boolean; pts: Pt[]; len: number[]};

export type Plan = {
  W: number;
  H: number;
  pulse: number;
  pin: number;
  colors: Record<string, string>;
  ease: {enter: number[]; exit: number[]; move: number[]};
  layout: PhotoLayout;
  /** the style card's finish and closer, its two faces' families, and the person's handle */
  finish: Finish;
  closerShape: string;
  faces: {display: string; text: string; italic: boolean};
  handle: string;
  fps: number;
  /** the map's paper grain, the card's finish grain: a card with none draws flat color */
  grain: number;
  land: number[][];
  cards: Card[];
  legs: Leg[];
  hook: {kicker: Line[]; name: number; dive: number; settle: number};
  closer: {at: number; window: Box; title: string; signoff: string; route: number; still: number; paper: number};
  end: number;
};

/** Beats after the next stop's beat begins that the camera lands on it. */
export const LAND = 0.15;
/** Beats after the camera leaves a near place that the next place's photograph begins to open, and that the one it
 * leaves begins to fold; the most beats a fold takes. */
const OPEN_AFTER = 0.15;
const FOLD_AFTER = 0.2;
const FOLD = 0.75;
/** A lift folds the photograph it leaves off the map first, over LIFT_FOLD beats from the camera leaving, so the leg
 * lies bare while the dot runs it, and opens the next one out of its pin over LIFT_OPEN beats as its beat begins. */
const LIFT_FOLD = 0.25;
const LIFT_OPEN = 0.3;
/** The hook's photograph opens out of its pin while the camera comes down onto it, from HOOK_OPEN of the way from the
 * dive to the settle. */
const HOOK_OPEN = 0.35;

/** How far a card stands off the map while it is the one the camera is on: far enough that the map behind it slides at
 * a rate of its own as the camera turns about the card. */
export const liftOf = (c: Card) => 420 * c.s;

/** A card's timings in beats: when it opens out of its pin and when it folds onto the map, each as [start, length]. */
export const timesOf = (c: Card) => ({open: [c.openAt, c.openLen], fold: [c.foldAt, c.foldLen]});

const lengths = (pts: Pt[]) => {
  const out = [0];
  for (let i = 1; i < pts.length; i++) out.push(out[i - 1] + Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]));
  return out;
};

/** The point `u` (0 to 1) of the way along a leg by its length. */
export const along = (leg: Leg, u: number): Pt => {
  const total = leg.len[leg.len.length - 1];
  const d = Math.min(1, Math.max(0, u)) * total;
  let k = 1;
  while (k < leg.len.length - 1 && leg.len[k] < d) k++;
  const a = leg.pts[k - 1], b = leg.pts[k];
  const seg = leg.len[k] - leg.len[k - 1];
  const f = seg > 0 ? (d - leg.len[k - 1]) / seg : 0;
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
};

/** A color the board names: a role of the card's palette, else the hex itself. */
export const colorOf = (plan: Plan, name?: string) => plan.colors[name ?? 'ink'] ?? name ?? plan.colors.ink;

export const planOf = (board: Board): Plan => {
  const route = board.route as any;
  const {fps} = board.format;
  const pulse = (fps * 60) / board.bpm;
  const starts: Record<string, number> = {};
  let f = 0;
  for (const b of board.beats) {
    starts[b.id] = f / pulse;
    f += b.frames ?? Math.round(b.bars * 4 * pulse);
  }
  const end = f / pulse;
  const C = starts.closer ?? end;
  const raw: CardIn[] = route.cards;
  const legs: Leg[] = route.legs.map((l: Omit<Leg, 'len'>) => ({...l, len: lengths(l.pts)}));
  const settle: number = route.hook.settle;
  const cards: Card[] = [];
  raw.forEach((c, i) => {
    const arrive = starts[c.id];
    const leave = i + 1 < raw.length ? starts[raw[i + 1].id] : C;
    const prev = cards[i - 1];
    const near = prev && !legs[i - 1]?.far;
    const lift = near && prev.travel === 'lift';
    const dive: number = route.hook.dive;
    const openAt = i === 0 ? dive + HOOK_OPEN * (settle - dive) : !near ? arrive - 0.1 : lift ? arrive : prev.goAt + OPEN_AFTER;
    const openLen = i === 0 ? (settle - dive) * (1 - HOOK_OPEN) : lift ? LIFT_OPEN : near ? arrive + LAND - openAt : 0.35;
    cards.push({...c, T: {s: c.s, o: c.o}, arrive, leave, cutAt: arrive + c.cut, goAt: leave - c.go, landAt: leave + LAND,
      openAt, openLen, foldAt: leave - c.go, foldLen: Math.min(FOLD, c.go + 0.1)});
  });
  // before a near place the fold waits while the next photograph opens, and still ends where the print lands beside its
  // pin; a lift folds first
  cards.forEach((c, i) => {
    if (!legs[i] || legs[i].far) return;
    if (c.travel === 'lift') {
      c.foldLen = LIFT_FOLD;
      return;
    }
    c.foldAt += FOLD_AFTER;
    c.foldLen -= FOLD_AFTER;
  });
  const sys = board.system;
  return {
    W: route.W, H: route.H, pulse, pin: route.pin, colors: route.colors,
    ease: {enter: sys.ease.enter, exit: sys.ease.exit, move: sys.ease.move},
    layout: sys.photo, grain: sys.finish.grain, finish: sys.finish, closerShape: sys.closer,
    faces: {display: sys.display.family, text: sys.text.family, italic: Boolean(sys.display.italic)}, handle: board.handle ?? '', fps,
    land: route.land, cards, legs, hook: route.hook,
    closer: {at: C, window: route.closer.window, title: route.closer.title, signoff: route.closer.signoff,
      route: route.closer.route, paper: route.closer.paper, still: board.sound?.find((c) => c.kind === 'stop')?.at ?? end},
    end,
  };
};

const openEase = bezier([0.12, 0.8, 0.25, 1]);

/** How far card `c` has opened out of its pin at beat `t`, and how far it has folded onto its print, 0 to 1 each; in
 * the closer every print sinks back into its pin, so the closer's map carries the route and the names alone. */
export const progressOf = (plan: Plan, c: Card, t: number) => {
  const tm = timesOf(c);
  const settle = c.i === 0 ? bezier([0.3, 0, 0.2, 1]) : openEase;
  return {opening: span(t, tm.open[0], tm.open[1], settle), fold: span(t, tm.fold[0], tm.fold[1], bezier(plan.ease.move)),
    sink: span(t, plan.closer.at, 0.6, bezier(plan.ease.move))};
};

/** A card's color, a role or a hex, as a hex. */
const toneOf = (plan: Plan, v: string) => {
  const hex = plan.colors[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut, and closer: the frame, the card's colors, tones, grid, print and faces, the
 * hook's photograph, and the board's own words. */
export const lookOf = (plan: Plan): Look => {
  const g = plan.layout.grid;
  const pic = plan.layout.picture;
  const m = g.margin * plan.W;
  return {
    W: plan.W, H: plan.H, fps: plan.fps, pulse: plan.pulse, colors: plan.colors,
    display: plan.faces.display, text: plan.faces.text, italic: plan.faces.italic,
    title: plan.closer.title, handle: plan.handle, signoff: plan.closer.signoff,
    tone: {
      ground: toneOf(plan, plan.layout.ground), dip: plan.finish.dip === 'none' ? null : toneOf(plan, plan.finish.dip),
      matte: toneOf(plan, plan.finish.matte), light: toneOf(plan, plan.finish.light), pen: toneOf(plan, pic.penColor),
      rim: toneOf(plan, pic.rimColor), tape: toneOf(plan, pic.tapeColor),
    },
    grid: {
      m, rules: g.rules,
      cols: Array.from({length: g.cols + 1}, (_, i) => m + (i * (plan.W - 2 * m)) / g.cols),
      rows: Array.from({length: g.rows + 1}, (_, i) => m + (i * (plan.H - 2 * m)) / g.rows),
    },
    finished: plan.finish.words !== 'clean',
    photo: plan.cards[0] ? staticFile(plan.cards[0].file) : undefined,
    print: {
      box: [Math.max(0, pic.box[0]) * plan.W, Math.max(0, pic.box[1]) * plan.H,
        (Math.min(1, pic.box[0] + pic.box[2]) - Math.max(0, pic.box[0])) * plan.W, (Math.min(1, pic.box[1] + pic.box[3]) - Math.max(0, pic.box[1])) * plan.H],
      rim: pic.rim * plan.W, tilt: pic.tilt, tape: pic.tape,
    },
  };
};
