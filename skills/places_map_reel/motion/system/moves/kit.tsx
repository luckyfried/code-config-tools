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

/** A line of the board's words. */
export const Words: React.FC<{text: string; family: string; size: number; color: string; style?: CSSProperties}> = ({text, family, size, color, style}) => (
  <div style={{fontFamily: `'${family}'`, fontSize: size, lineHeight: 1.12, color, whiteSpace: 'pre-wrap', ...style}}>{text}</div>
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
 * letters. */
export const measure = (text: string, family: string, size: number, weight = 400, tracking = 0) => {
  if (!pad) pad = document.createElement('canvas').getContext('2d');
  if (!pad) return text.length * size * 0.56;
  pad.font = `${weight} ${size}px '${family}'`;
  return pad.measureText(text).width + Math.max(0, text.length - 1) * tracking * size;
};

/** The size the widest of `lines` is set at to span `width` px, as an end card sets its title: the measure decides,
 * and `most` only keeps a single short word from filling a whole frame. */
export const fitTo = (lines: string[], family: string, width: number, {weight = 400, tracking = 0, most = Infinity} = {}) => {
  const w = Math.max(1, ...lines.map((ln) => measure(ln, family, 100, weight, tracking)));
  return Math.min(most, (100 * width) / w);
};

/** `text` broken into at most `n` lines at word breaks. Of every way to break it into k lines, the best is the one
 * whose longest line is shortest, then the one whose lines are most even. k is the most lines, up to `n`, whose best
 * break leaves no line shorter than half the longest, so a short word never stands alone beside a long line. */
export const balance = (text: string, n: number): string[] => {
  const ws = wordsOf(text);
  const splits = (from: number, left: number): string[][] =>
    left === 1 ? [[ws.slice(from).join(' ')]]
      : Array.from({length: ws.length - left + 1 - from}, (_, j) => from + 1 + j)
        .flatMap((at) => splits(at, left - 1).map((rest) => [ws.slice(from, at).join(' '), ...rest]));
  const score = (ls: string[]) => {
    const lens = ls.map((l) => l.length);
    return [Math.max(...lens), Math.max(...lens) - Math.min(...lens), Math.min(...lens)];
  };
  for (let k = Math.min(Math.max(n, 1), ws.length); k > 1; k--) {
    const best = splits(0, k).reduce((a, b) => {
      const [wa, sa] = score(a), [wb, sb] = score(b);
      return wb < wa || (wb === wa && sb < sa) ? b : a;
    });
    const [most, , least] = score(best);
    if (least * 2 >= most) return best;
  }
  return [ws.join(' ')];
};

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
