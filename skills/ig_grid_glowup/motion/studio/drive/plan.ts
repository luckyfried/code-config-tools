// The drive film's plan, read from its board: the wall of posts and the moves that step it along, the frame's and
// the camera's keys, the band's words, each next post's times, and the closer. All times are musical beats from the
// film's start (the board's units, half a second each); all places are px of the format's frame, y down. The card's
// moves, cuts and closer read the timeline and the look, whose times are beats of the music. scripts/drive.py writes
// every value here but the look's tones, grid, print and photograph, which the card gives and lookOf reads.
import {staticFile} from 'remotion';
import type {Board} from '../../system/types';
import type {Pt} from '../../system/three/motion';
import type {Look} from '../../system/moves';
import type {Timeline} from '../../system/moves/layer';

export type Box = [number, number, number, number];
export type UV = [number, number, number, number];

// a line enters whole from its rise, or `by` letter or word, `stagger` beats apart, each tracked `track` em out and
// closing up as it lands
export type Line = {
  text: string; x: number; y: number; size: number; face: string; weight: number; color: string; tracking: number; name: string;
  by?: 'letter' | 'word'; stagger?: number; track?: number;
};

// `mute`: how far a post of theirs is taken toward gray beside the new ones
export type Cell = {key: string; file: string; uv: UV; slot: number; from: number; mute?: number};
export type Grid = {x0: number; y0: number; cw: number; ch: number; g: number; cols: number};
export type FrameKey = {t: number; box: Box; z: number; ease: 'move' | 'land' | 'close' | 'drop' | 'spring' | 'fall'};
// the side of the frame a band stands on: above the picture, or beside the frame with its top at the frame's top
export type BandSide = 'top' | 'left' | 'right';
export type BandKey = {t: number; open: number; band: string; side?: BandSide};
// `sink`: the beat the band's words sink back under their baselines
export type Band = {lines: Line[]; h: number; w?: number; rise?: Record<string, number>; sink?: number};
export type Framing = {c: Pt; h: number; z: number; fov: number; yaw: number; pitch: number; roll: number};
// `ease`: the curve of the move into the key, the plan's move curve when unset
export type CamKey = Framing & {t: number; arc: number; ease?: number[]; travel?: {warp?: number; burn?: number}};
export type Post = {
  n: number;
  beat: string;
  file: string;
  size: [number, number];
  uvSubject: UV;
  uv34: UV;
  // the photograph's recorded focus point in texture coordinates, which the held crop pushes in on
  uvFocal: Pt;
  whole: Box;
  crop: Box;
  z: number;
  slot: Box;
  // where a post that falls sets off from: the middle of the camera's view close on slot 0, px
  from?: Pt;
  // how the post comes into the grid: held whole and closed on (close), its crop sliding onto the station (slide), or
  // its cell falling from the lens into the grid (drop); `side` the way the move turns, 1 or -1
  move: 'close' | 'slide' | 'drop';
  side: number;
  full: boolean;
  // the film's peak, the held post read longest
  peak?: boolean;
  // the card's page a held post is read on
  page?: Page;
  times: {fly: [number, number]; close: [number, number]; drop: [number, number]; seat: number; reflow: [number, number]};
};

// a page of the card's photo layout, px of the frame and board beats: the photograph's picture box `pic` and the
// line box `box` ([x0, y0, x1, y1]), the card's ground round the picture, its words (each line's `y` its baseline, each
// word's `x` where it starts) in the display face entering from `at` on the card's `enter`, the label over them in its
// own face, a scrim of `scrim` under words set `over` the photograph, the frame's grid ruled in hairlines (`rules`);
// the paper closes in round the picture over `close` (there from the first frame when null), the words leave at
// `sink` and the paper opens out over `open`
export type PageWord = {text: string; x: number; at: number};
export type PageLine = {text: string; x: number; y: number; size: number; at: number; words: PageWord[]};
export type PageLabel = {text: string; x: number; y: number; size: number; face: 'display' | 'text'; weight: number; color: string; tracking: number; at: number};
export type Page = {
  pic: [number, number, number, number]; box: [number, number, number, number]; ground: string; over: boolean; enter: string;
  color: string; scrim: number; scrimColor: string; weight: number; tracking: number; lines: PageLine[]; label: PageLabel | null;
  rules: boolean; close: [number, number] | null; open: [number, number]; sink: number;
};

// a line of the closer's header, set as type a browser sets over the band's paper once the camera has stopped: px of
// the frame, `y` its baseline, `size` its em on screen, `at` the board beat it appears
export type HeaderLine = {text: string; x: number; y: number; size: number; face: 'display' | 'text'; bold: boolean; name: string; at: number};

export type Plan = {
  W: number;
  H: number;
  pulse: number;
  colors: Record<string, string>;
  // the key light's color: the card's burn, the color its light reads as on paper
  light: string;
  // the card's dust over the wall, 0 for none
  dust: number;
  ease: {enter: number[]; exit: number[]; move: number[]};
  // the card's moves over the film, in beats of the music, and the frames per beat of the music
  timeline: Timeline;
  look: Look;
  /** the style card's finish and its photo beat's layout */
  finish: Board['system']['finish'];
  photo: Board['system']['photo'];
  header: {at: number; lines: HeaderLine[]};
  // the hook's title page, none when the film has no title
  title: Page | null;
  closerShape: {name: string; at: number; still: number};
  cells: Cell[];
  reflows: [number, number][];
  grid: Grid;
  frame: FrameKey[];
  bandKeys: BandKey[];
  bands: Record<string, Band>;
  camera: CamKey[];
  posts: Post[];
  closer: {box: Box; lock: number; still: number};
  end: number;
};

/** The look drive.py writes: the frame, the music's pulse, the card's colors and faces, and the film's own words. */
type Base = Omit<Look, 'tone' | 'grid' | 'print' | 'finished' | 'photo'>;

/** A card's color, a role or a hex, as a hex. */
const toneOf = (colors: Record<string, string>, v: string) => {
  const hex = colors[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut, and closer: drive.py's look with the card's tones, its layout grid in frame px, its
 * print, whether its words take the finish, and the photograph the masked words are filled with (the film's peak post,
 * else its first). */
export const lookOf = (board: Board, base: Base, posts: Post[]): Look => {
  const {W, H} = base;
  const {finish, photo} = board.system;
  const colors = board.system.colors as unknown as Record<string, string>;
  const g = photo.grid;
  const pic = photo.picture;
  const m = g.margin * W;
  const shown = posts.find((p) => p.peak) ?? posts[0];
  return {
    ...base,
    tone: {
      ground: toneOf(colors, photo.ground), dip: finish.dip === 'none' ? null : toneOf(colors, finish.dip),
      matte: toneOf(colors, finish.matte), light: toneOf(colors, finish.light), pen: toneOf(colors, pic.penColor),
      rim: toneOf(colors, pic.rimColor), tape: toneOf(colors, pic.tapeColor),
    },
    grid: {
      m, rules: g.rules,
      cols: Array.from({length: g.cols + 1}, (_, i) => m + (i * (W - 2 * m)) / g.cols),
      rows: Array.from({length: g.rows + 1}, (_, i) => m + (i * (H - 2 * m)) / g.rows),
    },
    finished: finish.words !== 'clean',
    photo: shown ? staticFile(shown.file) : undefined,
    print: {
      box: [Math.max(0, pic.box[0]) * W, Math.max(0, pic.box[1]) * H,
        (Math.min(1, pic.box[0] + pic.box[2]) - Math.max(0, pic.box[0])) * W, (Math.min(1, pic.box[1] + pic.box[3]) - Math.max(0, pic.box[1])) * H],
      rim: pic.rim * W, tilt: pic.tilt, tape: pic.tape,
    },
  };
};

const layer = (board: Board, beat: string, kind: string) => board.beats.find((b) => b.id === beat)!.layers.find((l) => l.kind === kind)!;

export const planOf = (board: Board): Plan => {
  const {width: W, height: H, fps} = board.format;
  const pulse = (fps * 60) / board.bpm;
  const end = board.beats.reduce((n, b) => n + (b.frames ?? Math.round(b.bars * 4 * pulse)), 0) / pulse;
  const wall = layer(board, 'hook', 'Wall');
  const frame = layer(board, 'hook', 'Frame');
  const camera = layer(board, 'hook', 'Camera');
  const closer = layer(board, 'closer', 'Closer');
  const extra = board as unknown as {timeline: Timeline; look: Base; header: Plan['header']; closerShape: Plan['closerShape']; page?: Page | null};
  const posts = board.beats.filter((b) => b.id.startsWith('post-')).map((b) => b.layers.find((l) => l.kind === 'Post') as unknown as Post);
  return {
    W, H, pulse, colors: board.system.colors as unknown as Record<string, string>,
    light: board.system.finish.burn, dust: board.system.finish.dust,
    ease: {enter: board.system.ease.enter, exit: board.system.ease.exit, move: board.system.ease.move},
    timeline: extra.timeline, look: lookOf(board, extra.look, posts), finish: board.system.finish, photo: board.system.photo,
    header: extra.header, title: extra.page ?? null, closerShape: extra.closerShape,
    cells: wall.cells, reflows: wall.reflows, grid: wall.grid,
    frame: frame.keys, bandKeys: frame.bands, bands: frame.words,
    camera: camera.keys,
    posts,
    closer: {box: closer.box, lock: closer.lock, still: closer.still},
    end,
  };
};

/** A wall px point at depth z, in world space: x right from the frame's middle, y up. */
export const toWorld = (plan: Plan, p: Pt, z: number): [number, number, number] => [p[0] - plan.W / 2, plan.H / 2 - p[1], z];

/** The grid cell of a slot, as a box. */
export const cellBox = (g: Grid, slot: number): Box => {
  const c = slot % g.cols, r = Math.floor(slot / g.cols);
  return [g.x0 + c * (g.cw + g.g), g.y0 + r * (g.ch + g.g), g.cw, g.ch];
};
