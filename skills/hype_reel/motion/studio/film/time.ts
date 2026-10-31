// The film's clock: each beat's first frame and its frames per musical beat (snap set both from the music), the film's
// time at a frame in musical beats, and the beats as the moves, cuts and closer see them.
import {staticFile} from 'remotion';
import type {Timeline} from '../../system/moves/layer';
import type {Look} from '../../system/moves/types';
import {framesOf} from '../../system/system';
import type {Beat, Board} from '../../system/types';

export type Placed = {beat: Beat; i: number; from: number; frames: number; at: number; end: number; pulse: number};

export const placeBeats = (board: Board): Placed[] => {
  let f = 0;
  let at = 0;
  return board.beats.map((beat, i) => {
    const frames = framesOf(beat.len, beat.frames, board);
    const p = {beat, i, from: f, frames, at, end: at + beat.len, pulse: frames / Math.max(1, beat.len)};
    f += frames;
    at += beat.len;
    return p;
  });
};

/** The beat a frame falls in. */
export const placedAt = (placed: Placed[], frame: number) => {
  for (let i = placed.length - 1; i >= 0; i--) if (frame >= placed[i].from) return placed[i];
  return placed[0];
};

/** The film's time at a frame, in musical beats from its start. */
export const timeAt = (placed: Placed[], frame: number) => {
  const p = placedAt(placed, frame);
  return p.at + (frame - p.from) / p.pulse;
};

/** The beat the film is on at musical beat `t`. */
export const beatOfTime = (placed: Placed[], t: number) => {
  for (let i = placed.length - 1; i >= 0; i--) if (t >= placed[i].at) return placed[i];
  return placed[0];
};

/** The board's beats as the moves, cuts and closer see them. A beat the card's photo layout lays out carries the
 * photograph's box, the box its words are set in, and the beats the photograph is held whole (to its cut); its words
 * and label go in empty, because the kit sets them in the card's line box. A field beat's words go in empty too: the
 * kit slams them onto its ground. Any other beat covers the frame and gives its move its words. A beat with a picture
 * gives the moves its photograph and where it lies in the frame, so a move that flies to it or takes it apart lands
 * exactly where the camera holds it. */
export const timelineOf = (placed: Placed[]): Timeline => ({
  beats: placed.map((p) => {
    const b = p.beat;
    const pi = b.picture;
    const lands = pi ? {photo: staticFile(pi.file), place: [pi.box[0] + pi.place[0], pi.box[1] + pi.place[1], pi.place[2], pi.place[3]] as [number, number, number, number]} : {};
    const of = {id: b.id, form: b.form, at: p.at, end: p.end, move: b.move ?? undefined, transition: b.transition ?? null, peak: b.peak, ...lands};
    if (b.layout === 'field') return {...of, words: '', label: ''};
    const pic = b.layout === 'card' ? b.picture : null;
    if (!pic) return {...of, words: b.words, label: b.label};
    const [x, y, w, h] = pic.box;
    const type = b.lines.find((l) => l.box)?.box;
    return {...of, words: '', label: '', box: [x, y, x + w, y + h] as [number, number, number, number], type, held: [p.at, p.end] as [number, number]};
  }),
  cuts: placed.map((p) => p.at),
});

/** A card's color, a role of the board's colors or a hex, as a hex. */
const toneOf = (board: Board, v: string) => {
  const hex = (board.system.colors as Record<string, string>)[v] ?? v;
  if (!/^#[0-9a-fA-F]{6}$/.test(hex)) throw new Error(`MOVE_ERROR the card names no color ${v}`);
  return hex;
};

/** The film around every move, cut and closer: the frame, the card's colors, tones, grid, print and faces, whether
 * its words take the finish, the photograph the film's words are cut from (the reveal's, else the first one), every
 * photograph the film shows in its order, and the board's own words. */
export const lookOf = (board: Board): Look => {
  const {swatches: _, ...colors} = board.system.colors;
  const {width: W, height: H, fps} = board.format;
  const fin = board.system.finish;
  const photo = board.system.photo;
  const g = photo.grid;
  const m = g.margin * W;
  const pic = photo.picture;
  const ground = board.beats.find((b) => b.peak && b.picture) ?? board.beats.find((b) => b.picture);
  return {W, H, fps, pulse: (fps * 60) / board.bpm,
    colors: colors as Record<string, string>, display: board.system.display.family, text: board.system.text.family, italic: false,
    title: board.title, handle: board.handle, signoff: board.signoff,
    tone: {
      ground: toneOf(board, photo.ground), dip: fin.dip === 'none' ? null : toneOf(board, fin.dip), matte: toneOf(board, fin.matte),
      light: toneOf(board, fin.light), pen: toneOf(board, pic.penColor), rim: toneOf(board, pic.rimColor), tape: toneOf(board, pic.tapeColor),
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
    finished: fin.words !== 'clean',
    photo: ground?.picture ? staticFile(ground.picture.file) : undefined,
    photos: [...new Set(board.beats.flatMap((b) => (b.picture ? [b.picture.file] : [])))].map((f) => staticFile(f)),
  };
};
