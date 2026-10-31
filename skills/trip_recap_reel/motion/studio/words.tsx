// The film's own words, in the card's faces: the trip's name and its dates on the hook, placed at the hook's anchor; on
// each stop its place and its line in the card's line box, broken to fit it, coming on the way the card enters a line
// (rise, slam, type, fade or cut) once the cut into the beat has played, and leaving before the next cut. Over a
// photograph the card's scrim shades the frame under the words; on paper the words stand on the paper.
import React from 'react';
import {cutOf} from '../system/moves';
import {clamp01, span} from '../system/three/motion';
import type {Face} from '../system/types';
import {LABELS, LINES, shotAt, type Plan, type Shot} from './plan';

const faceOf = (plan: Plan, which: string): Face => (which === 'display' ? plan.system.display : plan.system.text);
const colorOf = (plan: Plan, role: string) => (plan.system.colors as Record<string, any>)[role] ?? role;

const cased = (face: Face, text: string) => (face.case === 'uppercase' ? text.toUpperCase() : face.case === 'lowercase' ? text.toLowerCase() : text);

const css = (face: Face, size: number): React.CSSProperties => ({
  fontFamily: `'${face.family}'`, fontWeight: face.weight, fontSize: size, lineHeight: face.lineHeight, letterSpacing: `${face.tracking}em`,
  fontVariationSettings: face.axes ? Object.entries(face.axes).map(([k, v]) => `'${k}' ${v}`).join(', ') : undefined,
  whiteSpace: 'pre',
});

let ctx: CanvasRenderingContext2D | null = null;
/** The width a line takes set in `face` at `size`, its tracking included. */
const widthOf = (face: Face, size: number, text: string) => {
  ctx = ctx ?? document.createElement('canvas').getContext('2d');
  if (!ctx) return text.length * size * 0.5;
  ctx.font = `${face.weight} ${size}px '${face.family}'`;
  return ctx.measureText(text).width + face.tracking * size * text.length;
};

/** The words broken into lines no wider than `width`, at the largest size from `most` down to half of it that takes at
 * most `lines` lines within `tall`. */
const setLines = (face: Face, text: string, most: number, width: number, lines: number, tall: number) => {
  const words = cased(face, text).split(/\s+/).filter(Boolean);
  for (let size = most; ; size = Math.floor(size * 0.94)) {
    const out: string[] = [];
    for (const w of words) {
      const last = out[out.length - 1];
      if (last !== undefined && widthOf(face, size, `${last} ${w}`) <= width) out[out.length - 1] = `${last} ${w}`;
      else out.push(w);
    }
    const fits = out.length <= lines && out.every((l) => widthOf(face, size, l) <= width) && out.length * size * face.lineHeight <= tall;
    if (fits || size <= most / 2) return {size, lines: out};
  }
};

/** When the words of a beat may come on: once the cut into it has played its first half. */
const startOf = (plan: Plan, shot: Shot) => {
  const at = shot.beat.at ?? 0;
  const c = cutOf(shot.beat.transition);
  return at + Math.max(0.25, c ? c.beats / 2 : 0);
};

/** How far a line is in at `t`, the way the card enters a line: each line's opacity, lift (px) and scale, and how many of
 * its letters show. */
const entered = (plan: Plan, enter: string, t: number, from: number, i: number, n: number, before = 0, total = n) => {
  const at = from + i * plan.system.ease.stagger * 2;
  if (enter === 'cut') return {o: t >= at ? 1 : 0, y: 0, s: 1, chars: n};
  if (enter === 'type') {
    // the lines type one after another as one sentence, a letter every 1.6 frames, and a long sentence faster, so the
    // whole of it is typed out within two beats and reads whole for the rest of its beat
    const per = Math.min(1.6, (2 * plan.pulse) / Math.max(1, total));
    const typed = t >= from ? Math.floor((t - from) * plan.pulse / per) + 1 : 0;
    const chars = Math.max(0, Math.min(n, typed - before));
    return {o: typed > before ? 1 : 0, y: 0, s: 1, chars};
  }
  if (enter === 'slam') {
    const v = clamp01((t - at) / 0.5);
    return {o: v > 0 ? 1 : 0, y: 0, s: 1 + 0.35 * (1 - v) * (1 - v), chars: n};
  }
  if (enter === 'fade') return {o: plan.enter(span(t, at, 1.5)), y: 0, s: 1, chars: n};
  const v = plan.enter(span(t, at, 0.9));
  return {o: v, y: 28 * (1 - v), s: 1, chars: n};
};

const Lines: React.FC<{plan: Plan; face: Face; size: number; lines: string[]; color: string; align: string; x: number; y: number; w: number;
  enter: string; t: number; from: number; out: number; shade: boolean; rotate?: number}> = ({plan, face, size, lines, color, align, x, y, w, enter, t, from, out, shade, rotate = 0}) => (
  <div style={{position: 'absolute', left: x, top: y, width: w, transform: `rotate(${rotate}deg)`, transformOrigin: align === 'center' ? '50% 0' : '0 0'}}>
    {lines.map((l, i) => {
      const before = lines.slice(0, i).reduce((a, x) => a + x.length, 0);
      const e = entered(plan, enter, t, from, i, l.length, before, lines.reduce((a, x) => a + x.length, 0));
      return (
        <div key={i} style={{...css(face, size), color, textAlign: align === 'center' ? 'center' : 'left', opacity: e.o * out,
          transform: `translateY(${e.y}px) scale(${e.s})`, transformOrigin: align === 'center' ? '50% 70%' : '0 70%',
          textShadow: shade ? `0 ${size * 0.04}px ${size * 0.4}px rgba(0,0,0,0.55)` : undefined}}>
          {l.slice(0, e.chars)}<span style={{opacity: 0}}>{l.slice(e.chars)}</span>
        </div>
      );
    })}
  </div>
);

export const Words: React.FC<{plan: Plan; t: number}> = ({plan, t}) => {
  const shot = shotAt(plan, t);
  if (!shot || t >= plan.closer.at) return null;
  const {W, H, area} = plan;
  const lay = plan.system.photo;
  const k = Math.min(W, H) / 1080;
  const at = shot.beat.at ?? 0, end = shot.beat.end ?? at + 4;
  const from = startOf(plan, shot);
  const nextCut = cutOf(plan.line.beats[shot.index + 1]?.transition);
  const leave = end - Math.max(0.5, nextCut ? nextCut.beats / 2 : 0);
  const out = 1 - plan.exit(span(t, leave - 0.6, 0.6));
  if (out <= 0) return null;
  const move = shot.beat.move ?? '';
  const aw = area[2] - area[0], ah = area[3] - area[1];
  const shade = shot.full;
  // over a whole-frame photograph the words take the end of the type area the board anchors them to, away from what the
  // photograph looks at and from a label the move sets; the card's line box gives their measure and their edge
  const low = (shot.line[1] + shot.line[3]) / 2 > (area[1] + area[3]) / 2;
  const flip = shot.full && shot.beat.form !== 'title' && (shot.beat.anchor === 'top' ? low : shot.beat.anchor === 'bottom' ? !low : false);
  const box: [number, number, number, number] = flip
    ? [shot.line[0], Math.max(area[1] + 0.06 * ah, area[1] + area[3] - shot.line[3]), shot.line[2], area[1] + area[3] - shot.line[1]]
    : shot.line;
  const up = flip ? !low : low;
  if (shot.beat.form === 'title') {
    if (LABELS.has(move) && move !== 'date-stamp') return null;
    const display = plan.system.display, text = faceOf(plan, 'text');
    const title = setLines(display, plan.title, Math.round(2.2 * lay.line.size * k), aw, 2, ah * 0.4);
    const kick = setLines(text, plan.kicker, Math.round(Math.max(lay.label.size, 0.75 * lay.line.size) * k), aw, 1, ah * 0.2);
    const tall = title.lines.length * title.size * display.lineHeight + 0.5 * kick.size + kick.size * text.lineHeight;
    const anchor = shot.beat.anchor ?? 'bottom';
    const top = anchor === 'top' ? area[1] + 0.06 * ah : anchor === 'middle' ? area[1] + (ah - tall) / 2 : box[3] - tall;
    const align = anchor === 'middle' || lay.line.align === 'center' ? 'center' : 'start';
    // the title waits for the move's opening (the bars parting, the print landing) before it comes on
    const start = at + 1;
    const scrim = shade ? lay.line.scrim * out * plan.enter(span(t, start - 0.5, 1)) : 0;
    const fade = H / 5;
    return (
      <div style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
        {scrim > 0 ? <div style={{position: 'absolute', left: 0, right: 0, top: top - fade, height: tall + 2 * fade,
          background: `linear-gradient(to bottom, rgba(0,0,0,0), rgba(0,0,0,${0.7 * scrim}) 35%, rgba(0,0,0,${0.7 * scrim}) 65%, rgba(0,0,0,0))`}} /> : null}
        <Lines plan={plan} face={display} size={title.size} lines={title.lines} color={colorOf(plan, lay.line.color)} align={align} x={area[0]} y={top} w={aw}
          enter={lay.line.enter} t={t} from={start} out={out} shade={shade} />
        <Lines plan={plan} face={text} size={kick.size} lines={kick.lines} color={colorOf(plan, lay.label.color)} align={align} x={area[0]}
          y={top + title.lines.length * title.size * display.lineHeight + 0.5 * kick.size} w={aw} enter={lay.line.enter} t={t} from={start + 1} out={out} shade={shade} />
      </div>
    );
  }
  const labelFace = faceOf(plan, lay.label.face), lineFace = faceOf(plan, lay.line.face);
  const showLabel = !(LABELS.has(move) && move !== 'date-stamp') && !LINES.has(move);
  const showLine = !LINES.has(move) && Boolean(shot.beat.words);
  const ls = Math.round(lay.label.size * k);
  const drop = showLabel ? ls * labelFace.lineHeight + 0.45 * ls : 0;
  // over a whole-frame photograph a line keeps the card's size in up to three lines, growing from the box's edge into the
  // frame rather than shrinking into the box; on a page the words keep to the box beside the print
  const room = shot.full ? Math.max(box[3] - box[1], 0.42 * ah) : box[3] - box[1];
  const line = setLines(lineFace, shot.beat.words, Math.round(lay.line.size * k), box[2] - box[0], 3, room - drop);
  const tall = drop + (showLine ? line.lines.length * line.size * lineFace.lineHeight : 0);
  const top = !shot.full ? box[1] + Math.max(0, (box[3] - box[1] - tall) / 2)
    : up ? box[3] - Math.max(tall, (box[3] - box[1] + tall) / 2) : box[1] + Math.max(0, (box[3] - box[1] - tall) / 2);
  const scrim = shade && lay.line.scrim > 0 ? lay.line.scrim * out * plan.enter(span(t, from - 0.25, 0.75)) : 0;
  // the scrim shades from the words to the frame's edge they sit nearer, fading out a sixth of the frame past them
  const lid = up ? top - H / 6 : 0;
  const foot = up ? H : top + tall + H / 6;
  const fadeAt = ((H / 6) / (foot - lid)) * 100;
  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      {scrim > 0 ? <div style={{position: 'absolute', left: 0, right: 0, top: lid, height: foot - lid,
        background: up ? `linear-gradient(to bottom, rgba(0,0,0,0), rgba(0,0,0,${scrim}) ${fadeAt}%, rgba(0,0,0,${scrim}))`
          : `linear-gradient(to top, rgba(0,0,0,0), rgba(0,0,0,${scrim}) ${fadeAt}%, rgba(0,0,0,${scrim}))`}} /> : null}
      {showLabel ? <Lines plan={plan} face={labelFace} size={ls} lines={[cased(labelFace, shot.stop.name)]} color={colorOf(plan, lay.label.color)}
        align={lay.line.align} x={box[0]} y={top} w={box[2] - box[0]} enter={lay.line.enter === 'type' ? 'type' : 'fade'} t={t} from={from} out={out}
        shade={shade} rotate={lay.line.rotate} /> : null}
      {showLine ? <Lines plan={plan} face={lineFace} size={line.size} lines={line.lines} color={colorOf(plan, lay.line.color)} align={lay.line.align}
        x={box[0]} y={top + drop} w={box[2] - box[0]} enter={lay.line.enter} t={t} from={from + (showLabel ? 0.5 : 0)} out={out} shade={shade}
        rotate={lay.line.rotate} /> : null}
    </div>
  );
};
