// The year film's plan, read from its board: the wall (the title, its underline, the year's rows and the closer's
// lines), each month's piece (its photograph, where the card stands it, its line and slit, its name and their line,
// where it sits on the wall, the card's move and cut picked for it, and when each of its moves runs), the hook's
// window, the closer's route, the card's finish, photo layout and closer, the board's beats as the moves read them,
// and the film's one grade. Places are px of the wall (the closer's frame, y down) or of a month's piece frame, which `T` maps
// onto the wall; times are musical beats from the film's start.
import {staticFile} from 'remotion';
import * as THREE from 'three';
import {bezier, span, type Pt} from '../../system/three/motion';
import type {Timeline} from '../../system/moves/layer';
import type {BeatOn, Look} from '../../system/moves/types';
import type {Beat, Board, Finish, PhotoLayout} from '../../system/types';
import type {Grade} from '../../system/three/travel';

export type Box = [number, number, number, number];

/** One line of type: px baseline at (x, y), turned `rotate` degrees clockwise about `pivot`. */
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
  /** the contrast it holds over the photograph under it, with its plate */
  contrast?: number;
};

/** A month's plate under its words: a box of its piece frame, its edges fading over `soft` px (the card's scrim, a
 * soft band from over the words to the frame's foot, or a close plate), turned with the words `rotate` degrees about
 * `pivot`, in the role `color` at `alpha`. */
export type Plate = {box: Box; soft: number; rotate: number; pivot: Pt; color: string; alpha: number};

/** A plate on the wall under a group of the wall's type (`of`: title, handle, labels or signoff); alpha 0 where the
 * type holds its contrast bare. */
export type WallPlate = {of: string; box: Box; color: string; alpha: number};

/** A piece frame's px mapped onto the wall: scaled by `s` about the origin, then moved by `o`. */
export type Xf = {s: number; o: Pt};
export const onWall = (T: Xf, p: Pt): Pt => [T.o[0] + T.s * p[0], T.o[1] + T.s * p[1]];

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
export const WALL: Xf = {s: 1, o: [0, 0]};

/** A row of the wall, one a month: its middle, its line's ends (every row's alike), the y its line settles on in the
 * dark under its band, the band its photograph spreads into, its name. */
export type Row = {y: number; x0: number; x1: number; rule: number; band: Box; label: Line};

/** A month's moves in film beats: [start, length] each, and when the camera arrives and the month ends. `card` is its
 * photograph opening out of its line, over the month before or as the camera leaves the hook's window. */
export type Phases = {card: Pt; arrive: number; draw: Pt; part: Pt; open: Pt; say: Pt; pull: Pt; fold: Pt; slide: Pt; end: number};

export type Month = {
  id: string;
  month: number;
  short: string;
  file: string;
  size: Pt;
  focus: Pt;
  scene: string;
  /** their own line from the post, as one string; empty when the month is wordless */
  text: string;
  /** the story's peak, which holds longest */
  peak: boolean;
  extra: string[];
  /** the photograph laid over the piece frame: x, y, width, height px */
  place: Box;
  /** where the card stands the photograph, piece px, or null where the card shows none */
  picture: Box | null;
  /** where the month's name and line stand, [x0, y0, x1, y1] piece px */
  box: Box;
  /** the picture runs past the frame's edges */
  full: boolean;
  /** the photograph's line in the piece frame: its y at the left edge and at the right edge */
  line: Pt;
  /** the slit's half thickness, piece px */
  band: number;
  /** how much of its light the band carries once it has spread into its row */
  gain: number;
  T: Xf;
  /** how far its photograph stands off the wall while it is open: each month higher than the one before */
  lift: number;
  row: Row;
  name: Line;
  /** their line, one Line a word, in reading order */
  said: Line[];
  /** the card's move and cut picked for what the photograph shows */
  move: string;
  transition: string | null;
  plate: Plate;
  start: number;
  beats: number;
  at: Phases;
};

export type Year = {
  title: Line;
  /** the year's heading at rest on the wall (wall px) */
  heading: Box;
  /** the photograph the wall lies on, the first month's, from the frame's top to its foot, softened and dimmed to `dim`
   * of its light like every month's field */
  ground: {month: string; box: Box; flat: string | null};
  dim: number;
  /** the title's underline: x0, y, x1 (wall px) */
  rule: [number, number, number];
  /** the right edge of the year (wall px) */
  reach: number;
  /** the handle from the export's profile files, or null for none */
  handle: Line | null;
  signoff: Line;
  plates: WallPlate[];
  rows: Row[];
  months: Month[];
  /** the hook: its window, the beats it changes photograph on (one a month, all alike) and the beat the last flash
   * ends, the months in the order they flash (the look's lead first), the camera's dive into it, and the beat of its
   * card */
  hook: {window: Box; flash: number[]; order: number[]; close: Pt; slam: Pt; dive: Pt; rest: number};
  /** the closer: the year's rows whole from `at`, the card's closer over the frame from `card`, the stop at `still` */
  closer: {at: number; card: number; still: number; end: number; hops: number[]};
  colors: Record<string, string>;
  /** the film's one grade, the card's turned by the person's palette, in display values (black and white points per
   * channel, midtone gamma, saturation), which the stage applies to every frame */
  grade: Grade;
};

export type Plan = Year & {W: number; H: number; fps: number; pulse: number; ease: {enter: number[]; move: number[]}; frames: number;
  photo: PhotoLayout; finish: Finish; closerShape: string; line: Timeline; look: Look};

/** A beat of the year's board: where it starts and ends in musical beats, and the words and label its move is handed. */
type YearBeat = Beat & {at: number; end: number; words: string; label: string; peak: boolean};

export const planOf = (board: Board): Plan => {
  const y = (board as unknown as {year: Year}).year;
  const {width: W, height: H, fps} = board.format;
  const frames = board.beats.reduce((n, b) => n + (b.frames ?? 0), 0);
  const pulse = (fps * 60) / board.bpm;
  const sys = board.system;
  // the board's beats as the moves read them, each cut on its beat's start; a photo beat hands its move no words, since
  // the card's photo layout sets them, and names where its photograph and its words stand and when the camera holds on it
  const byId = new Map(y.months.map((m) => [m.id, m]));
  const whole: Box = [-0.06 * W, -0.06 * H, 1.06 * W, 1.06 * H];
  const beats: BeatOn[] = (board.beats as YearBeat[]).map((b) => {
    const m = b.form === 'photo' ? byId.get(b.id) : undefined;
    return {id: b.id, form: b.form ?? 'photo', at: b.at, end: b.end, move: b.move, transition: b.transition,
      words: b.form === 'photo' ? '' : b.words, label: b.form === 'photo' ? '' : b.label, peak: b.peak,
      ...(m ? {box: m.picture ?? whole, type: m.box, held: [m.at.arrive, m.at.pull[0]] as Pt} : {})};
  });
  const plan = {...y, W, H, fps, pulse, ease: {enter: sys.ease.enter, move: sys.ease.move}, frames, photo: sys.photo, finish: sys.finish,
    closerShape: sys.closer, line: {beats, cuts: beats.map((b) => b.at)}};
  return {...plan, look: lookOf(plan, sys)};
};

/** A card's color, a role or a hex, as a hex. */
const toneOf = (colors: Record<string, string>, v: string) => {
  const hex = colors[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut, and closer: the frame, the card's colors, tones, grid and faces, and the year's own
 * words. */
const lookOf = (plan: Omit<Plan, 'look'>, sys: Board['system']): Look => {
  const {W, H, photo, finish, colors} = plan;
  const g = photo.grid;
  const pic = photo.picture;
  const m = g.margin * W;
  const ground = plan.months.find((x) => x.id === plan.ground.month) ?? plan.months[0];
  return {
    W, H, fps: plan.fps, pulse: plan.pulse, colors, display: sys.display.family, text: sys.text.family, italic: Boolean(sys.display.italic),
    title: plan.title.text, handle: plan.handle?.text ?? '', signoff: plan.signoff.text,
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
    photo: ground ? staticFile(ground.file) : undefined,
    print: {
      box: [Math.max(0, pic.box[0]) * W, Math.max(0, pic.box[1]) * H,
        (Math.min(1, pic.box[0] + pic.box[2]) - Math.max(0, pic.box[0])) * W, (Math.min(1, pic.box[1] + pic.box[3]) - Math.max(0, pic.box[1])) * H],
      rim: pic.rim * W, tilt: pic.tilt, tape: pic.tape,
    },
  };
};

/** A wall point at height `z` in world space (x right, y up, z toward the camera). */
export const world = (plan: Plan, p: Pt, z = 0) => new THREE.Vector3(p[0] - plan.W / 2, plan.H / 2 - p[1], z);

/** The y of a month's line at piece x. */
export const lineY = (m: Month, W: number, x: number) => m.line[0] + ((m.line[1] - m.line[0]) * x) / W;

/** How far an open month stands off the wall. */
export const liftOf = (m: Month) => m.lift;

/** The camera's field of view on a month, degrees. */
export const HOLD_FOV = 30;

/** How far the near layer stands in front of the far one at its fullest, as a share of the camera's distance. */
const SEP = 0.12;

/** A month's near layer (the photograph over its line, with the month's words and their plate, and the accent line on
 * its cut) at beat `t`: how far it stands in front of the far one (the photograph under the line, and the slit), wall
 * px, how far that is of its fullest (0 to 1), its piece frame on the wall and its height. The near layer is scaled toward the camera's axis by as much as it
 * stands nearer, so from the month's station the two layers line up into the one photograph, and any move of the
 * camera slides one against the other. It stands off as the photograph opens and is back on the far one by the moment
 * the month is left, before the next month's photograph opens over it. */
export const layerOf = (plan: Plan, m: Month, t: number): {sep: number; on: number; T: Xf; z: number} => {
  const a = m.at;
  const s = m.T.s;
  const D = (plan.H * s) / 2 / Math.tan((HOLD_FOV * Math.PI) / 360);
  const ease = bezier(plan.ease.move);
  // a full frame's near layer stands off its far one; a picture in the card's box lies flat in it, since its edges
  // would part where a full frame runs past the frame
  const sep = m.full ? SEP * D * span(t, a.open[0], 0.6, ease) * (1 - span(t, a.pull[0] - 0.6, 0.6, ease)) : 0;
  const k = (D - sep) / D;
  const axis: Pt = [m.T.o[0] + (s * plan.W) / 2, m.T.o[1] + (s * plan.H) / 2];
  return {sep, on: sep / (SEP * D), T: {s: s * k, o: [axis[0] + k * (m.T.o[0] - axis[0]), axis[1] + k * (m.T.o[1] - axis[1])]}, z: liftOf(m) + sep};
};

/** Where a bar rests: a hair over the bars before it. */
export const restZ = (index: number) => 0.04 * (index + 1);

/** The month the film is on at beat `t` (the last one whose drawing has begun), or null in the hook. */
export const monthAt = (plan: Plan, t: number) => [...plan.months].reverse().find((m) => t >= m.start - 0.4) ?? null;
