// The sign-off on the card's closer and the dot that ends it. Each closer the year's looks end on sets the sign-off in
// the frame over the picture (system/moves/closer); `cardStop` lays out the same lines, sizes and boxes that closer
// does, read from the look, and puts the full stop on the last line's baseline just past its last letter. Through the
// card the dot is drawn over the picture, above the card, and flies on to that full stop, so the sign-off's full stop is
// the dot that travelled the whole film.
import * as THREE from 'three';
import {balance, fitTo, measure, OUT, px, smoothNoise, SNAP, span} from '../../system/moves/kit';
import type {Look} from '../../system/moves/types';
import type {Pt} from '../../system/three/motion';
import {screenOf, wallUnder} from './camera';
import {dotAt, TRAIL, type Route} from './dot';
import type {Plan} from './plan';

let pad: CanvasRenderingContext2D | null = null;

/** How far the baseline lies below the top of a line box `lh` em tall, px. */
const baseline = (family: string, size: number, weight: number, lh: number) => {
  if (!pad) pad = document.createElement('canvas').getContext('2d');
  if (!pad) return size * (lh / 2 + 0.3);
  pad.font = `${weight} ${size}px '${family}'`;
  const m = pad.measureText('H');
  return (lh * size - (m.fontBoundingBoxAscent + m.fontBoundingBoxDescent)) / 2 + m.fontBoundingBoxAscent;
};

/** A full stop in the frame: its middle and radius, px. */
export type Stop = {p: Pt; r: number};

/** The full stop of a line set at `size` whose last letter ends at `x` on baseline `base`, as the wall's full stops sit. */
const after = (x: number, base: number, size: number): Stop => {
  const r = Math.max(6, 0.09 * size);
  return {p: [x + 0.06 * size + r, base - r], r};
};

/** The sign-off's full stop on the card's closer `shape`, `local` beats into it and `u` of the way to its stop, in
 * frame px, moving as the closer moves the line; null for a closer that sets no sign-off. */
export const cardStop = (look: Look, shape: string, local: number, u: number): Stop | null => {
  if (shape === 'closing-flicker') {
    const calm = 1 - span(u, 0.6, 0.4);
    const dx = calm * px(look, 6) * smoothNoise(local * 8, 2), dy = calm * px(look, 9) * smoothNoise(local * 6, 5);
    const side = px(look, 110);
    const lines = balance(look.signoff, look.signoff.length > 30 ? 3 : look.signoff.length > 12 ? 2 : 1);
    const size = Math.min(fitTo(lines, look.display, look.W - 2 * side, {most: px(look, 220)}), (look.H * 0.5) / (lines.length * 1.05));
    const top = look.H * 0.44 - (lines.length * size * 1.05) / 2;
    // the lines are centred on the frame
    const s = after(look.W / 2 + measure(lines[lines.length - 1], look.display, size) / 2,
      top + (lines.length - 1) * size * 1.05 + baseline(look.display, size, 400, 1.05), size);
    return {p: [s.p[0] + dx, s.p[1] + dy], r: s.r};
  }
  if (shape === 'letter-build') {
    const words = look.signoff.toUpperCase().split(/\s+/).filter(Boolean);
    const inset = px(look, 60);
    const size = Math.min(fitTo(words, look.display, look.W - 2 * inset, {weight: 800, tracking: -0.03}), (look.H * 0.6) / (words.length * 0.92));
    // a word a line, then the handle, the block centred in the frame above its foot margin
    const tall = words.length * 0.92 * size + (look.handle ? px(look, 48) + 1.12 * px(look, 44) : 0);
    const top = inset + (look.H - inset - look.H * 0.12 - tall) / 2;
    const last = words[words.length - 1];
    // each letter its own box, the tracking after every letter
    const x = inset + [...last].reduce((w, ch) => w + measure(ch, look.display, size, 800) - 0.03 * size, 0);
    const s = after(x, top + (words.length - 1) * 0.92 * size + baseline(look.display, size, 800, 0.92), size);
    // the block eases toward the viewer about its middle until the stop
    const k = 0.96 + 0.04 * span(u, 0, 1, OUT);
    const cx = look.W / 2, cy = top + tall / 2;
    return {p: [cx + (s.p[0] - cx) * k, cy + (s.p[1] - cy) * k], r: s.r * k};
  }
  if (shape === 'poster') {
    const g = look.grid;
    const measureW = look.W - 2 * g.m;
    const row = (i: number) => g.rows[Math.min(g.rows.length - 1, i)];
    const title = look.title || look.signoff;
    const lines = balance(title, title.length > 12 ? 2 : 1);
    const said = look.title ? balance(look.signoff, look.signoff.length > 24 ? 2 : 1) : [];
    const saidSize = said.length ? Math.min(px(look, 66), fitTo(said, look.text, measureW * 0.75)) : 0;
    const top = row(1) + px(look, 60);
    const room = row(g.rows.length - 2) - top - (said.length ? said.length * saidSize * 1.2 + px(look, 50) : 0) - px(look, 30);
    const size = Math.min(fitTo(lines, look.display, measureW, {weight: 700, tracking: -0.035, most: px(look, 300)}), room / (lines.length * 0.95));
    if (said.length) {
      // the closing line under the title, in the text face
      const y0 = top + lines.length * size * 0.95 + px(look, 50);
      return after(g.m + measure(said[said.length - 1], look.text, saidSize),
        y0 + (said.length - 1) * 1.2 * saidSize + baseline(look.text, saidSize, 400, 1.2), saidSize);
    }
    // the sign-off is the title, rising onto its place over the closer's first third
    const rise = (1 - span(u, 0, 0.3, SNAP)) * px(look, 30);
    return after(g.m - size * 0.04 + measure(lines[lines.length - 1], look.display, size, 700, -0.035),
      top + rise + (lines.length - 1) * 0.95 * size + baseline(look.display, size, 700, 0.95), size);
  }
  return null;
};

/** How far through the card's closer beat `t` is, 0 to 1, as the closer counts it. */
const closerU = (plan: Plan, t: number) => Math.min(1, (t - plan.closer.card) / Math.max(0.05, plan.closer.still - plan.closer.card));

/** The sign-off's full stop where the card's closer sets it as the film stops, as the wall point under it at the dot's
 * height; null when the card's closer sets no sign-off. */
export const signoffStop = (plan: Plan): {p: THREE.Vector3; r: number} | null => {
  const {card, still} = plan.closer;
  const s = plan.closerShape ? cardStop(plan.look, plan.closerShape, still - card, 1) : null;
  if (!s) return null;
  const p = wallUnder(plan, still, s.p, 2.5);
  return {p, r: wallUnder(plan, still, [s.p[0] + s.r, s.p[1]], 2.5).x - p.x};
};

/** The dot and its trail over the card from the card's first frame: where the picture shows the dot, moved with the
 * card's line, so it flies on through the card and lands as the sign-off's full stop, in the accent itself once it has
 * landed. */
export const CardDot: React.FC<{plan: Plan; t: number; route: Route}> = ({plan, t, route}) => {
  const {card, still} = plan.closer;
  if (t < card) return null;
  const now = plan.closerShape ? cardStop(plan.look, plan.closerShape, t - card, closerU(plan, t)) : null;
  const end = plan.closerShape ? cardStop(plan.look, plan.closerShape, still - card, 1) : null;
  const shift: Pt = now && end ? [now.p[0] - end.p[0], now.p[1] - end.p[1]] : [0, 0];
  const accent = new THREE.Color(plan.colors.accent);
  const head = dotAt(plan, t, route);
  const moving = t < Math.round(still * plan.pulse) / plan.pulse;
  /** A world point's place in the frame, and how many frame px one world px is there. */
  const seen = (p: THREE.Vector3) => {
    const [x, y] = screenOf(plan, t, p);
    const [ex, ey] = screenOf(plan, t, p.clone().setX(p.x + 1));
    return {x: x + shift[0], y: y + shift[1], s: Math.hypot(ex - x, ey - y)};
  };
  const dots = Array.from({length: TRAIL}, (_, i) => {
    const k = i === 0 ? head : dotAt(plan, t - i * 0.025, route);
    const fall = 1 - i / TRAIL;
    const {x, y, s} = seen(k.p);
    return {
      x, y, r: k.r * s * (i === 0 ? 1 : 0.85 * fall + 0.15),
      // the trail is the dot's motion: once it has landed there is none
      on: i === 0 || (k.p.distanceTo(head.p) > 2 && moving),
      color: (i === 0 && moving ? accent.clone().multiplyScalar(1.5) : accent).getStyle(), alpha: k.glow * (i === 0 ? 1 : 0.5 * fall * fall),
    };
  });
  return (
    <>
      {dots.reverse().filter((d) => d.on && d.alpha > 0.002).map((d, i) => (
        <div key={i} style={{position: 'absolute', left: d.x - d.r, top: d.y - d.r, width: 2 * d.r, height: 2 * d.r, borderRadius: '50%', background: d.color, opacity: d.alpha}} />
      ))}
    </>
  );
};
