// The drive film's plan, read from its board: the hook's photograph of them together and every person's card, where
// each lands on the closer's wall, when it arrives and leaves, its stamp, its words and its tag, and the closer's
// route across the wall, the beat's move and the cut into it as the style card names them, and the card's closer.
// All times are musical beats from the film's start; all places are px of the closer's frame
// (the wall), y down.
import {staticFile} from 'remotion';
import type {Board, Finish, Layer, PhotoLayout} from '../../system/types';
import type {Pt} from '../../system/three/motion';
import type {Timeline} from '../../system/moves/layer';
import type {Look} from '../../system/moves/types';

export type Box = [number, number, number, number];

/** One line of type as the boards set it: px baseline at (x, y), turned `rotate` degrees clockwise about `pivot`, set
 * in the static font `file`. */
export type Line = {
  text: string;
  x: number;
  y: number;
  size: number;
  file?: string;
  face?: string;
  weight?: number;
  tracking?: number;
  color?: string;
  rotate?: number;
  pivot?: Pt;
  anchor?: string;
  name?: string;
  /** a line over a picture too busy to read it on stands on a thin strip of the other color this many px across */
  strip?: number;
};

/** A tag as the boards set it: a pill holding `text`, its pointer's point at `tip`, the pill in `box`, the pointer
 * reaching up to the tip from a pill below it or down to it from a pill above. A tag in a look's own `shape` has no
 * pointer: a `band` of the accent across the frame with the text from `inset` px (a marquee when it names `scroll`, px
 * a beat), a solid `block`, a `sticker` with a white edge, or a `stamp`: a thin frame of `ink` round text in `ink`;
 * each turned `turn` degrees clockwise about its middle. */
export type Tag = {text: string; file: string; size: number; tip: Pt; box: Box; side: 'below' | 'above';
  shape?: 'band' | 'block' | 'sticker' | 'stamp'; inset?: number; scroll?: number; turn?: number; ink?: string};

/** A piece frame's px mapped onto the wall: scaled by `s` about the origin, then moved by `o`. */
export type Xf = {s: number; o: Pt};
export const onWall = (T: Xf, p: Pt): Pt => [T.o[0] + T.s * p[0], T.o[1] + T.s * p[1]];
export const WALL: Xf = {s: 1, o: [0, 0]};

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
  /** the person's place in the film's order; 0 for the hook's photograph of them together */
  n: number;
  hook: boolean;
  file: string;
  /** the edge in the piece frame: y at its left side and at its right side */
  line: Pt;
  /** what stands over the edge once the blade has cut: a ground color, or `photo` where the photograph itself does */
  field: string;
  /** the photograph laid whole in the piece frame */
  place: Box;
  /** a framed photograph: the band of its picture it spans (fractions of the picture's height), and how the style
   * mounts that print on its card: `taped` on the page, `projected` on the dark, `flat` on the ink */
  band: Pt | null;
  mount: string | null;
  /** how the card arrives (board_drive.py's DRAWN: drop, slap, rise, pop, slide, cut, slam, stretch) and how its stamp
   * lands (underline, date, slam, stretch) */
  entry: string;
  words: string;
  /** how its own words enter: rising a word at a time (rise), slammed down a word at a time (slam), or typed (type) */
  say: string;
  /** the dark that rises behind its type over a photograph that fills the frame: clear at y `from`, `dark` from y `to`
   * to the frame's foot, px of the piece frame */
  scrim: [number, number, number, ('x' | 'y')?] | null;
  /** a print standing on the page: the x its sides are cropped to, px of the piece frame */
  crop: Pt | null;
  /** the smaller print taped in the page's lower third under the caption: its photograph, the box its picture fills
   * (piece-frame px, before its turn), the part of the photograph it shows (fractions, top down) and its turn, degrees */
  keepsake: {file: string; box: Box; uv: Box; turn: number} | null;
  T: Xf;
  /** the card's slice on the closer's wall (top left, top right, bottom right, bottom left); a card with none takes
   * the next card's, so it trims away under that card */
  slot: Pt[];
  /** when the card arrives and when the film cuts to the next beat; the card then rests in its slice */
  arrive: number;
  leave: number;
  /** when its tag closes and leaves for the next card */
  go: number;
  /** when the blade crosses the edge */
  cut: number;
  /** the stamp of where and when the photograph was taken, landing on the edge as the blade cuts */
  stamp: Line | null;
  rest: Line[];
  /** when the rest of the card's words start to rise */
  restAt: number;
  /** the stamp's line on the closer's wall */
  slotStamp: Line | null;
  /** the closer's lines that carry this card's other lines, by name */
  slotRest: Record<string, Line>;
  /** the card's tags (one per head on the hook), when the first lands and how far apart they land */
  tags: Tag[];
  tagAt: number;
  tagStep: number;
  /** the person's tag on the closer's wall */
  wallTag: Tag | null;
  /** the box, in its piece frame's px, that its type and tags fill */
  keep: Box | null;
};

export type Plan = {
  W: number;
  H: number;
  /** the format's safe area: left, top, right, bottom px */
  safe: Box;
  pulse: number;
  /** seconds a beat lasts */
  beat: number;
  colors: Record<string, string>;
  ease: {enter: number[]; move: number[]};
  finish: Finish;
  /** the card's photo beat: the ground a framed print is mounted on, its rim, and the tape that holds it */
  photo: PhotoLayout;
  /** the color a tag's text reads in on the accent */
  tagText: string;
  /** the beats with their moves and cuts, for the shared moves' nudges and travel (`line`), and the same beats with
   * only the moves whose drawing stands over the cards (`over`); the film's look as the moves read it */
  line: Timeline;
  over: Timeline;
  look: Look;
  cards: Card[];
  /** the hook's handle and year, and its title standing on the edge, rising from `titleAt` */
  kicker: Line[];
  title: Line[];
  titleAt: number;
  /** when the hook's tags gather into one */
  gather: number;
  /** when the closer lands, its ground, its own lines, the route the tag runs across the wall, `still`: where the
   * picture and the sound stop together and the wall holds, and `height`: the wall's, px (the frame's, or taller when
   * its rows need more room than the frame gives them) */
  closer: {at: number; ground: string; lines: Line[]; route: {at: number; len: number}; still: number; height: number;
    shape: {name: string; at: number} | null;
    /** when the tag lands on the last person and the wall stands whole */
    walled: number};
  end: number;
};

/** Beats from a card's arrival to the blade's cut (board_drive.py's CUT), and on the hook (HOOK_BLADE). */
const LIFT = 1.0;
const HOOK_BLADE = 0.3;
/** Beats before the cut that a card's tag closes and leaves for the next card. */
const TAG_LEAD = 0.4;
/** The shared moves whose drawing stands over a card without covering it: the rest are drawn by the cards themselves
 * (DRAWN in board_drive.py) and only nudge the camera or add to its travel. */
const OVER = new Set(['light-leak', 'gate-weave', 'stack-and-split']);

const kindOf = (layers: Layer[], kind: string) => layers.filter((l) => l.kind === kind);

/** A card's color, a role or a hex, as a hex. */
const toneOf = (colors: Record<string, string>, v: string) => {
  const hex = colors[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** Where a card's photograph stands in the frame while the camera holds it at its station, [x0, y0, x1, y1] px: the
 * picture under the edge (on a card whose field is the photograph, the whole picture), inside the frame. */
const boxOf = (c: Card, W: number, H: number): Box => {
  const [px, py, pw, ph] = c.place;
  const top = c.field === 'photo' ? py : Math.max(py, Math.min(c.line[0], c.line[1]));
  return [Math.max(0, px), Math.max(0, top), Math.min(W, px + pw), Math.min(H, py + ph)];
};

/** The film around every move, cut, and closer: the frame, the card's colors, tones, grid, print and faces, the
 * photograph of them together, and the board's own words. */
const lookOf = (board: Board, W: number, H: number, fps: number, pulse: number, photo: string | undefined): Look => {
  const sys = board.system;
  const colors = sys.colors as unknown as Record<string, string>;
  const g = sys.photo.grid;
  const pic = sys.photo.picture;
  const m = g.margin * W;
  return {
    W, H, fps, pulse, colors, display: sys.display.family, text: sys.text.family, italic: !!sys.display.italic,
    title: '', handle: board.said_by ?? '', signoff: board.signoff ?? '',
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
  const people = board.beats.filter((b) => b.id.startsWith('person-'));
  const order = board.beats.map((b) => b.id);
  const nextStart = (id: string) => {
    const i = order.indexOf(id);
    return i + 1 < order.length ? starts[order[i + 1]] : end;
  };

  const cardOf = (beatId: string, n: number): Card => {
    const beat = byId[beatId];
    const hook = n === 0;
    const cut = kindOf(beat.layers, 'Cut')[0];
    // a card with no slice on the wall (the hook's photograph of them together) lies over the whole wall
    const slice = slices.find((s) => s.owner === n);
    const s = slice ? (slice.place as Box)[2] / (cut.place as Box)[2] : 1;
    const T: Xf = slice ? {s, o: [(slice.place as Box)[0] - s * (cut.place as Box)[0], (slice.place as Box)[1] - s * (cut.place as Box)[1]]} : WALL;
    const wordLayers = kindOf(beat.layers, 'Words');
    const words = wordLayers.flatMap((l) => l.lines as Line[]);
    const stamp = hook ? null : words.find((l) => l.name?.startsWith('stamp-')) ?? null;
    const rest = hook ? [] : words.filter((l) => l !== stamp);
    const restLayer = wordLayers.find((l) => (l.lines as Line[]).some((x) => rest.includes(x)));
    const arrive = starts[beatId];
    const restNamed = Object.fromEntries(rest.filter((l) => l.name && named[l.name]?.text === l.text).map((l) => [l.name!, named[l.name!]]));
    const tl = kindOf(beat.layers, 'Tags')[0];
    return {
      key: beatId, n, hook, file: cut.photo.file, line: cut.line as Pt, field: cut.field ?? 'paper', place: cut.place as Box, T,
      band: (cut.photo.band ?? null) as Pt | null, mount: cut.photo.mount ?? null, entry: cut.entry ?? 'rise', words: cut.words ?? 'rise',
      say: cut.say ?? 'rise', scrim: (cut.scrim ?? null) as [number, number, number, ('x' | 'y')?] | null, crop: (cut.crop ?? null) as Pt | null,
      keepsake: (cut.keepsake ?? null) as Card['keepsake'],
      slot: (slice?.poly ?? []) as Pt[], arrive, leave: nextStart(beatId), cut: arrive + (hook ? HOOK_BLADE : LIFT),
      go: nextStart(beatId) - TAG_LEAD,
      stamp, rest, restAt: arrive + (restLayer?.at ?? LIFT + 0.35),
      slotStamp: stamp?.name ? named[stamp.name] ?? null : null, slotRest: restNamed,
      tags: (tl?.tags ?? []) as Tag[], tagAt: arrive + (tl?.at ?? 0.25), tagStep: tl?.step ?? 0, wallTag: (slice?.tag ?? null) as Tag | null,
      keep: (beat.keep ?? null) as Box | null,
    };
  };

  const hookBeat = byId.hook;
  const hookWords = kindOf(hookBeat.layers, 'Words');
  const title = hookWords.flatMap((l) => l.lines as Line[]).filter((l) => l.name?.startsWith('title-'));
  const kicker = hookWords.flatMap((l) => l.lines as Line[]).filter((l) => !title.includes(l));
  const titleLayer = hookWords.find((l) => (l.lines as Line[]).some((x) => title.includes(x)));
  const cards: Card[] = [cardOf('hook', 0), ...people.map((p) => cardOf(p.id, Number(p.id.split('-')[1])))];
  // a card with no slice trims into the next card's, under that card, as the camera leaves it
  cards.forEach((c, i) => { if (!c.slot.length) c.slot = cards[i + 1]?.slot ?? cards[i - 1].slot; });
  // a closer line is carried onto the wall by the card it belongs to; the rest rise as the tag lands on the last
  const carried = new Set<Line>(cards.flatMap((c) => [...(c.slotStamp ? [c.slotStamp] : []), ...Object.values(c.slotRest)]));
  const C = starts.closer ?? end;
  const route = kindOf(closer.layers, 'Route')[0];
  const shape = kindOf(closer.layers, 'Shape')[0];
  const sys = board.system;
  // a photo beat's box, its type's box and the beats the camera holds it, so a move lays its marks on the photograph
  // and lifts them before the cut; every word of a beat is the card's own to set, so a move is handed none
  const beats = board.beats.map((b, i) => {
    const form = b.form ?? (b.id === 'hook' ? 'title' : b.id === 'closer' ? 'wall' : 'photo');
    const c = cards.find((x) => x.key === b.id);
    return {
      id: b.id, form, at: starts[b.id],
      end: i + 1 < order.length ? starts[order[i + 1]] : end, move: b.move, transition: i === 0 ? null : b.transition ?? null,
      words: '', label: '', peak: b.id === order[order.length - 2],
      ...(c && form === 'photo' ? {box: boxOf(c, W, H), ...(c.keep ? {type: c.keep} : {}), held: [c.arrive, c.go] as Pt} : {}),
    };
  });
  const cuts = beats.map((b) => b.at);
  const look = lookOf(board, W, H, fps, pulse, cards[0]?.file);
  return {
    W, H, safe: (board.format.safe ?? [0, 0, W, H]) as Box, pulse, beat: 60 / board.bpm, colors: board.system.colors as unknown as Record<string, string>,
    ease: {enter: board.system.ease.enter, move: board.system.ease.move}, finish: sys.finish, photo: sys.photo, look, tagText: (sys.colors as unknown as Record<string, string>)[board.tag_text ?? 'paper'] ?? sys.colors.paper,
    line: {beats, cuts}, over: {beats: beats.map((b) => ({...b, move: b.move && OVER.has(b.move) ? b.move : undefined})), cuts},
    cards, kicker, title, titleAt: titleLayer?.at ?? 1.6, gather: kindOf(hookBeat.layers, 'Tags')[0]?.gather ?? 2.9,
    closer: {at: C, ground: kindOf(closer.layers, 'Cut')[0]?.field ?? 'paper', lines: closerLines.filter((l) => !carried.has(l)),
      route: {at: C + (route?.at ?? 0.9), len: route?.beats ?? 4}, still: board.sound?.find((c) => c.kind === 'stop')?.at ?? end,
      height: Math.max(H, route?.height ?? H), shape: shape ? {name: shape.name, at: C + (shape.at ?? 0)} : null,
      walled: C + (route?.at ?? 0.9) + (route?.beats ?? 4)},
    end,
  };
};
