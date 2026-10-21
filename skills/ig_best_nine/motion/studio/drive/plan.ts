// The drive film's plan, read from its board: every photograph's card, where it lands on the closer's wall, when it
// arrives and leaves, its count and its words, and the ribbon and closer that end the film. All times are musical
// beats from the film's start; all places are px of the closer's frame (the wall), y down.
import type {Board, Layer} from '../../system/types';
import type {Pt} from '../../system/three/motion';

export type Box = [number, number, number, number];

/** One line of type as the boards set it: px baseline at (x, y), turned `rotate` degrees clockwise about `pivot`. */
export type Line = {
  text: string;
  x: number;
  y: number;
  size: number;
  face?: string;
  weight?: number;
  tracking?: number;
  color?: string;
  rotate?: number;
  pivot?: Pt;
  anchor?: string;
  name?: string;
  count?: [number, number, number];
};

/** A piece frame's px mapped onto the wall: scaled by `s` about the origin, then moved by `o`. */
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
  rank: number;
  hook: boolean;
  file: string;
  /** the edge in the piece frame: y at its left side and at its right side */
  line: Pt;
  field: string;
  /** the photograph laid whole in the piece frame */
  place: Box;
  T: Xf;
  /** the card's slice on the closer's wall (top left, top right, bottom right, bottom left) */
  slot: Pt[];
  arrive: number;
  leave: number;
  /** when the blade crosses the edge */
  cut: number;
  count: Line | null;
  value: number;
  /** the figure its count rolls up from */
  from: number;
  rest: Line[];
  /** the count's line on the closer's wall */
  slotCount: Line | null;
  /** the closer's lines that carry this card's rank and caption, by name */
  slotRest: Record<string, Line>;
};

export type Bar = {a: Pt; b: Pt; share: number; rank: number; file: string; label: string};

export type Plan = {
  W: number;
  H: number;
  pulse: number;
  colors: Record<string, string>;
  ease: {enter: number[]; move: number[]};
  cards: Card[];
  /** the hook's total and the hook's other lines */
  total: Line | null;
  kicker: Line[];
  /** when the total breaks into the counts */
  breakAt: number;
  shards: {rank: number; value: number; size: number}[];
  ribbon: {at: number; len: number; bars: Bar[]};
  /** when the closer lands, its ground, its own lines, and `still`: where the picture and the sound stop together and the wall holds */
  closer: {at: number; ground: string; lines: Line[]; still: number};
  end: number;
};

/** Beats from a card's arrival to the blade's cut: the photograph holds clean, then the dot draws the line (as drive.py's BLADE and SWEEP). */
const LIFT = 1.3;

const kindOf = (layers: Layer[], kind: string) => layers.filter((l) => l.kind === kind);
const digits = (s: string) => Number(s.replace(/[^\d]/g, '')) || 0;

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
  const byId = Object.fromEntries(board.beats.map((b) => [b.id, b]));
  const closer = byId.closer;
  const slices = kindOf(closer.layers, 'Slice');
  const closerLines: Line[] = kindOf(closer.layers, 'Words').flatMap((l) => l.lines as Line[]);
  const named = Object.fromEntries(closerLines.filter((l) => l.name).map((l) => [l.name!, l]));
  const pieces = board.beats.filter((b) => b.id.startsWith('piece-'));
  const order = board.beats.map((b) => b.id);
  const nextStart = (id: string) => {
    const i = order.indexOf(id);
    return i + 1 < order.length ? starts[order[i + 1]] : end;
  };
  const top = Math.max(...pieces.map((p) => digits((kindOf(p.layers, 'Words')[0].lines[0] as Line).text)));

  const cardOf = (beatId: string, rank: number, hook: boolean, prev: number): Card => {
    const beat = byId[beatId];
    const cut = kindOf(beat.layers, 'Cut')[0];
    const piece = byId[`piece-${rank}`];
    const pieceCut = kindOf(piece.layers, 'Cut')[0];
    const slice = slices.find((s) => s.owner === rank)!;
    const s = (slice.place as Box)[2] / (pieceCut.place as Box)[2];
    const T: Xf = {s, o: [(slice.place as Box)[0] - s * (pieceCut.place as Box)[0], (slice.place as Box)[1] - s * (pieceCut.place as Box)[1]]};
    const words = kindOf(beat.layers, 'Words').flatMap((l) => l.lines as Line[]);
    const count = hook ? null : words.find((l) => l.name?.startsWith('count-')) ?? null;
    const rest = hook ? [] : words.filter((l) => l !== count);
    const arrive = starts[beatId];
    const restNamed = Object.fromEntries(rest.filter((l) => l.name && named[l.name]?.text === l.text).map((l) => [l.name!, named[l.name!]]));
    return {
      key: beatId, rank, hook, file: cut.photo.file, line: cut.line as Pt, field: cut.field ?? 'paper', place: cut.place as Box, T,
      slot: slice.poly as Pt[], arrive, leave: nextStart(beatId), cut: arrive + (hook ? 0.3 : LIFT),
      count, value: count ? digits(count.text) : 0, from: prev, rest,
      slotCount: count?.name ? named[count.name] ?? null : null, slotRest: restNamed,
    };
  };

  const hookBeat = byId.hook;
  const hookWords = kindOf(hookBeat.layers, 'Words').flatMap((l) => l.lines as Line[]);
  const total = hookWords.find((l) => l.count) ?? null;
  const kicker = hookWords.filter((l) => l !== total);
  const cards: Card[] = [cardOf('hook', 1, true, 0)];
  let prev = 0;
  for (const p of pieces) {
    const rank = Number(p.id.split('-')[1]);
    const c = cardOf(p.id, rank, false, prev);
    cards.push(c);
    prev = c.value;
  }
  const ranked = cards.filter((c) => !c.hook);
  // a closer line is carried onto the wall by the card it belongs to; the rest rise when the closer lands
  const carried = new Set<Line>(ranked.flatMap((c) => [...(c.slotCount ? [c.slotCount] : []), ...Object.values(c.slotRest)]));
  const bars: Bar[] = ranked.map((c) => ({a: c.slot[3], b: c.slot[2], share: c.value / top, rank: c.rank, file: c.file, label: c.count?.text ?? String(c.value)}));
  return {
    W, H, pulse, colors: board.system.colors as unknown as Record<string, string>,
    ease: {enter: board.system.ease.enter, move: board.system.ease.move},
    cards, total, kicker, breakAt: 2.75,
    shards: ranked.map((c) => ({rank: c.rank, value: c.value, size: Math.sqrt(c.value / top)})),
    ribbon: {at: starts.nine ?? end, len: (starts.closer ?? end) - (starts.nine ?? end), bars},
    closer: {at: starts.closer ?? end, ground: kindOf(closer.layers, 'Cut')[0]?.field ?? 'accent', lines: closerLines.filter((l) => !carried.has(l)),
      still: board.sound?.find((c) => c.kind === 'stop')?.at ?? end},
    end,
  };
};
