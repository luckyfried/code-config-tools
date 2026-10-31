// The parts the moves, cuts, and closers are drawn with: whole-frame layers, a window cut in a field, a line of the
// board's words fitted to a width, and the curves in beats every one of them times itself by.
import React, {useEffect, useState, type CSSProperties} from 'react';
import {continueRender, delayRender} from 'remotion';
import {bezier, clamp01, hash, smoothNoise, span} from '../three/motion';
import type {Look} from './types';

export {bezier, clamp01, hash, smoothNoise, span};

export const fill: CSSProperties = {position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, pointerEvents: 'none'};

/** px of a 1080-wide frame, at this frame's width. */
export const px = (look: Look, v: number) => (v * look.W) / 1080;

/** A field of `color` over the whole frame with a window [x, y, w, h] (frame px) cut out of it, the picture showing
 * through the window. */
export const Window: React.FC<{box: [number, number, number, number]; color: string; radius?: number; rotate?: number; style?: CSSProperties; children?: React.ReactNode}> = ({box, color, radius = 0, rotate = 0, style, children}) => (
  <div style={{position: 'absolute', left: box[0], top: box[1], width: box[2], height: box[3], borderRadius: radius,
    boxShadow: `0 0 0 6000px ${color}`, transform: `rotate(${rotate}deg)`, ...style}}>{children}</div>
);

/** The size a line of `chars` characters is set at to span `width` px, never above `most`. */
export const fit = (chars: number, width: number, most: number, em = 0.56) => Math.min(most, width / Math.max(1, chars * em));

/** How shared words are drawn in a face with an optical-size axis: at the axis's default, the instance every measure
 * stands at (the board's measure in Python, `measure` here, and the 3D type), so words placed from a measure stand where
 * it put them. */
export const OPTICAL: CSSProperties = {fontOpticalSizing: 'none'};

/** A line of the board's words. */
export const Words: React.FC<{text: string; family: string; size: number; color: string; style?: CSSProperties}> = ({text, family, size, color, style}) => (
  <div style={{fontFamily: `'${family}'`, fontSize: size, lineHeight: 1.12, color, whiteSpace: 'pre-wrap', ...OPTICAL, ...style}}>{text}</div>
);

/** A curve through the card's easing in, as a function of progress. */
export const OUT = bezier([0.22, 1, 0.36, 1]);
export const SNAP = bezier([0.76, 0, 0.24, 1]);
export const SINE = bezier([0.37, 0, 0.63, 1]);

/** A damped overshoot landing at 1: 0 at u = 0, settled by u = 1. */
export const land = (u: number) => {
  const v = clamp01(u);
  return 1 - Math.exp(-6 * v) * Math.cos(v * Math.PI * 2.5);
};

/** The words of a line, one a beat. */
export const wordsOf = (text: string) => text.split(/\s+/).filter(Boolean);

/** A hex color at opacity `a`. */
export const alpha = (hex: string, a: number) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${Math.max(0, Math.min(1, a)).toFixed(3)})`;
};

/** A color's luminance, 0 to 1. */
export const lumOf = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return (0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)) / 255;
};

let pad: CanvasRenderingContext2D | null = null;
/** The width in px of `text` set in `family` at `size`, measured on the loaded face, with `tracking` em between
 * letters. The face is measured at 100 px and scaled, where an optical-size axis of every card's face stands at its
 * default, the instance the words are drawn at (OPTICAL). */
export const measure = (text: string, family: string, size: number, weight = 400, tracking = 0) => {
  if (!pad && typeof document !== 'undefined') pad = document.createElement('canvas').getContext('2d');
  if (!pad) return text.length * size * 0.56;
  pad.font = `${weight} 100px '${family}'`;
  return (pad.measureText(text).width * size) / 100 + Math.max(0, text.length - 1) * tracking * size;
};

/** The size the widest of `lines` is set at to span `width` px, as an end card sets its title: the measure decides,
 * and `most` only keeps a single short word from filling a whole frame. */
export const fitTo = (lines: string[], family: string, width: number, {weight = 400, tracking = 0, most = Infinity} = {}) => {
  const w = Math.max(1, ...lines.map((ln) => measure(ln, family, 100, weight, tracking)));
  return Math.min(most, (100 * width) / w);
};

/** Whether a set of lines leaves a word alone: it has more than one line and one of them holds a single word. */
export const alone = (lines: string[]) => lines.length > 1 && lines.some((l) => wordsOf(l).length === 1);

/** The share of a set's size a set that leaves no word alone may give up and still be taken over it. */
export const LONE = 0.7;

/** The size a set of lines takes when a caller gives none: the measure over its longest line, in characters. */
const byLength = (ls: string[]) => 1 / Math.max(1, ...ls.map((l) => l.length));

/** Every way to break the words `ws` into `k` lines, in order. */
const splitsOf = (ws: string[], k: number): string[][] => {
  const go = (from: number, left: number): string[][] =>
    left === 1 ? [[ws.slice(from).join(' ')]]
      : Array.from({length: ws.length - left + 1 - from}, (_, j) => from + 1 + j)
        .flatMap((at) => go(at, left - 1).map((rest) => [ws.slice(from, at).join(' '), ...rest]));
  return k >= 1 && k <= ws.length ? go(0, k) : [];
};

/** `text` broken into at most `n` lines at word breaks. Of every way to break it into k lines, the best is the one
 * whose longest line is shortest, then the one whose lines are most even. k is the most lines, up to `n`, whose best
 * break leaves no line shorter than half the longest. A set that leaves a word alone on a line gives way to the set of
 * no more lines that leaves none alone and sets the largest, when that set's size is LONE of its size or more: the
 * text resets with a word more on a line, or a line fewer, at the smaller size. `sizeOf` is the size the caller sets a
 * set of lines at (by default the measure over the longest line in characters). */
export const balance = (text: string, n: number, sizeOf: (lines: string[]) => number = byLength): string[] => {
  const ws = wordsOf(text);
  const score = (ls: string[]) => {
    const lens = ls.map((l) => l.length);
    return [Math.max(...lens), Math.max(...lens) - Math.min(...lens), Math.min(...lens)];
  };
  let set = [ws.join(' ')];
  for (let k = Math.min(Math.max(n, 1), ws.length); k > 1; k--) {
    const best = splitsOf(ws, k).reduce((a, b) => {
      const [wa, sa] = score(a), [wb, sb] = score(b);
      return wb < wa || (wb === wa && sb < sa) ? b : a;
    });
    const [most, , least] = score(best);
    if (least * 2 >= most) {
      set = best;
      break;
    }
  }
  if (!alone(set)) return set;
  let held: string[] | null = null, heldSize = 0;
  for (let k = set.length; k >= 1; k--) {
    for (const ls of splitsOf(ws, k)) {
      if (alone(ls)) continue;
      const sz = sizeOf(ls);
      if (sz > heldSize + 1e-9 || (held && Math.abs(sz - heldSize) <= 1e-9 && score(ls)[1] < score(held)[1])) [held, heldSize] = [ls, sz];
    }
  }
  return held && heldSize >= LONE * sizeOf(set) ? held : set;
};

/** Whether a set leaves a short word, four letters or fewer, alone on a line: a short word joins the line before it. */
export const shortAlone = (lines: string[]) =>
  lines.length > 1 && lines.some((l) => {
    const ws = wordsOf(l);
    return ws.length === 1 && ws[0].replace(/[^\p{L}\p{N}]/gu, '').length <= 4;
  });

/** The lines a move that sets its words as large as they go takes, and their size: of every way to break the words into
 * one line up to `most`, and up to a line for every two words (two lines at least), that leaves no short word alone, the
 * one `sizeOf` sets largest, unless it leaves a word alone on a line and a set that leaves none alone sets at LONE of its
 * size or more, which is taken. */
export const setLines = (text: string, most: number, sizeOf: (lines: string[]) => number) => {
  const ws = wordsOf(text);
  let best = {lines: [ws.join(' ')], size: sizeOf([ws.join(' ')])}, held = best;
  for (let k = 2; k <= Math.min(most, ws.length, Math.max(2, Math.ceil(ws.length / 2))); k++) {
    for (const lines of splitsOf(ws, k)) {
      if (shortAlone(lines)) continue;
      const size = sizeOf(lines);
      if (size > best.size) best = {lines, size};
      if (!alone(lines) && size > held.size) held = {lines, size};
    }
  }
  return held.size >= LONE * best.size ? held : best;
};

/** The forms whose picture a move that sets the beat's words lands them over, the picture dimmed into the card's
 * ground: a photograph, or a clip playing under them. */
export const PICTURED = new Set(['photo', 'clip']);

/** The handle's size in every closer, px of a 1080 wide frame. */
export const HANDLE = 44;

/** The handle's color and opacity on `ground`: on a dark ground the card's light tone at full opacity, so it reads on
 * the last frame; on a light ground `ink` at opacity `a`. */
export const handleOn = (look: Look, ground: string, ink: string, a: number) =>
  lumOf(ground) < 0.4 ? {color: look.tone.light, opacity: 1} : {color: ink, opacity: a};

/** The photograph's box on a beat, [x, y, w, h] px: the box the card stands it in on a photo beat, the frame
 * otherwise. */
export const pictureOf = (look: Look, beat: {box?: [number, number, number, number]}): [number, number, number, number] => {
  if (!beat.box) return [0, 0, look.W, look.H];
  const x0 = Math.max(0, beat.box[0]), y0 = Math.max(0, beat.box[1]), x1 = Math.min(look.W, beat.box[2]), y1 = Math.min(look.H, beat.box[3]);
  return [x0, y0, x1 - x0, y1 - y0];
};

/** The safe area every word at rest stands inside, [x0, y0, x1, y1] px: the profile's, else the frame inset by the
 * grid's margin. */
export const safeOf = (look: Look): [number, number, number, number] => {
  const s = look.safe ?? {top: look.grid.m, bottom: look.grid.m, left: look.grid.m, right: look.grid.m};
  return [s.left, s.top, look.W - s.right, look.H - s.bottom];
};

/** One column and one row of the card's grid on a beat, px: the frame grid's pitch laid over the photograph's box on a
 * beat the card gives a box, so a move that steps by a cell steps by a cell of the picture it is given; the frame
 * grid's own pitch otherwise. */
export const cellOf = (look: Look, beat: {box?: [number, number, number, number]}) => {
  const {cols, rows} = look.grid;
  const [, , bw, bh] = pictureOf(look, beat);
  const nc = Math.max(1, cols.length - 1), nr = Math.max(1, rows.length - 1);
  return beat.box ? {col: bw / nc, row: bh / nr} : {col: (cols[cols.length - 1] - cols[0]) / nc, row: (rows[rows.length - 1] - rows[0]) / nr};
};

/** How much a mark drawn on the photograph shows at beat `t`: whole while the camera holds on it, gone over the first
 * of the pull back to the wall, so a mark never hangs over the wall. */
export const heldOf = (beat: {held?: [number, number]}, t: number) => (beat.held ? 1 - span(t, beat.held[1], 0.35) : 1);

/** The transform that keeps a layer drawn on the picture on the picture while a move's nudge turns the camera: the
 * nudge's move and scale, undone about the frame's middle. */
export const follow = (look: Look, n: {scale?: number; dx?: number; dy?: number}) => {
  const s = n.scale ?? 1;
  return {transformOrigin: '50% 50%', transform: `scale(${1 / s}) translate(${-(n.dx ?? 0) * look.H}px, ${-(n.dy ?? 0) * look.H}px)`} as CSSProperties;
};

/** The part of `box` outside `inner` (both [x, y, w, h] px) filled with `color`: a window cut in a field that ends at
 * the box, so nothing outside the box (a label, a line of words) is covered. The field reaches 1 px past the box on
 * every side, so the photograph's soft edge never shows as a hairline around it. */
export const Mat: React.FC<{box: [number, number, number, number]; inner: [number, number, number, number]; color: string}> = ({box: [x0, y0, w0, h0], inner: [ix, iy, iw, ih], color}) => {
  const x = x0 - 1, y = y0 - 1, w = w0 + 2, h = h0 + 2;
  const r = (k: string, l: number, t: number, ww: number, hh: number) =>
    ww > 0.5 && hh > 0.5 ? <div key={k} style={{position: 'absolute', left: l, top: t, width: ww + 0.5, height: hh + 0.5, background: color}} /> : null;
  return (
    <>
      {r('t', x, y, w, iy - y)}
      {r('b', x, iy + ih, w, y + h - iy - ih)}
      {r('l', x, iy, ix - x, ih)}
      {r('r', ix + iw, iy, x + w - ix - iw, ih)}
    </>
  );
};

/** Of `choices`, the color that stands furthest from `bg` in luminance: the ink words are set in on that ground. */
export const inkOn = (bg: string, choices: string[]) =>
  choices.reduce((a, b) => (Math.abs(lumOf(b) - lumOf(bg)) > Math.abs(lumOf(a) - lumOf(bg)) ? b : a));

const decoded = new Set<string>();

/** Whether the photograph at `src` has decoded; the frame waits for it the first time, so a move that draws the
 * photograph itself never renders a frame without it. */
export const usePhoto = (src: string | undefined) => {
  const [ready, setReady] = useState(() => !src || decoded.has(src));
  useEffect(() => {
    if (!src || ready) return;
    const handle = delayRender(`photograph ${src}`);
    const im = new Image();
    im.src = src;
    im.decode().catch(() => undefined).then(() => {
      decoded.add(src);
      setReady(true);
      continueRender(handle);
    });
  }, [src, ready]);
  return ready;
};
