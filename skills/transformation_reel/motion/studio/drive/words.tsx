// The story film's type in the camera's space, set as one system. A card's lines enter as the style card's lines do:
// rising letter by letter (each letter through its baseline past its place and back while the line's tracking closes
// from a little open to its own, the last letter landed within the board's `letters` of the first, and leaving the
// same way, sinking), or fading up, slamming down from oversize, typed on, or cut on, and those leave fading, before
// its print drops. On a card its date, their line (extruded) and on a chapter their next line enter on the print's
// paper label as the print lifts toward the lens, riding it, so the line has landed when the camera does, and stand in
// ink there, under or over the photograph and never on it; in the closer, once the camera has settled on the whole
// wall, their two dates, then the ask rise on the course of plain plaster across the wall. A line on the plaster
// stands over its own ink shadow; a line on paper has none.
import * as THREE from 'three';
import {bezier, clamp01} from '../../system/three/motion';
import {Type3D} from '../../system/three/Type3D';
import {fileOf, type Font} from '../../system/three/type';
import {onPrint} from './card';
import type {Card, Line, Plan} from './plan';

const DEPTH = 0.11;
/** a paper-colored line on the plaster stands over its own flat ink shadow; an ink line on the paper label has none */
const PAPER_SHADOW = 0.8;
const shadowOf = (ln: Line) => ((ln.color ?? 'ink') === 'ink' ? 0 : PAPER_SHADOW);
/** the beats one letter takes to rise, and to sink */
const ONE_IN = 0.32;
const ONE_OUT = 0.15;
/** how open a line's tracking starts, in em per letter: each letter comes in from this far to the right of its place */
const OPEN = 0.05;
type Fonts = Map<string, Font>;
type At = {x: number; y: number; size: number};

/** A line's baseline frame in world space: its start at (x, y) on the wall at depth `z`, its extrusion scaled by
 * `deep`, the whole grown by `scale`. */
export const frameOf = (plan: Plan, p: At, z: number, deep = 1, scale = 1) => {
  const m = new THREE.Matrix4().makeTranslation(p.x - plan.W / 2, plan.H / 2 - p.y, z);
  m.multiply(new THREE.Matrix4().makeScale(p.size * scale, p.size * scale, p.size * scale * deep));
  return m;
};

const fontOf = (fonts: Fonts, ln: Line) => fonts.get(fileOf(ln))!;
const colorOf = (plan: Plan, name?: string) => plan.colors[name ?? 'ink'] ?? name ?? plan.colors.ink;
const sink = bezier([0.55, 0, 0.8, 0.4]);

/**
 * The letters of a block of lines in at `a` over `len` beats and out at `b` over `out` beats (none when `b` is null),
 * counted across the block's lines in reading order: for line `j`, the rise and the offset of its letter `i` of `n`.
 */
const lettersOf = (plan: Plan, lines: Line[], t: number, a: number, len: number, b: number | null, out = plan.exit) => {
  const enter = bezier(plan.ease.enter);
  const before = lines.map((_, j) => lines.slice(0, j).reduce((s, ln) => s + [...ln.text].length, 0));
  const total = lines.reduce((s, ln) => s + [...ln.text].length, 0);
  const inStep = total > 1 ? Math.max(0, len - ONE_IN) / (total - 1) : 0;
  const outStep = total > 1 ? Math.max(0, out - ONE_OUT) / (total - 1) : 0;
  return (j: number) => (i: number): [number, number] => {
    const k = before[j] + i;
    const up = enter(clamp01((t - a - k * inStep) / ONE_IN));
    const down = b === null ? 0 : sink(clamp01((t - b - k * outStep) / ONE_OUT));
    return [up * (1 - down), OPEN * (1 - Math.min(1, up))];
  };
};

/** How a block of lines stands at `t` when the style card's lines do not rise letter by letter: `fade` comes up over
 * its entrance, `slam` drops onto its place from oversize on the card's entering ease, `type` sets one letter after
 * another, `cut` is simply there; each leaves fading over the exit, which starts at `b`. */
const standing = (plan: Plan, lines: Line[], t: number, a: number, len: number, b: number) => {
  const enter = bezier(plan.ease.enter);
  const gone = 1 - clamp01((t - b) / Math.max(0.05, plan.exit));
  const total = lines.reduce((s, ln) => s + [...ln.text].length, 0);
  const before = lines.map((_, j) => lines.slice(0, j).reduce((s, ln) => s + [...ln.text].length, 0));
  const u = clamp01((t - a) / Math.max(0.05, len));
  return (j: number) => {
    if (plan.enter === 'fade') return {opacity: enter(u) * gone, scale: 1, each: undefined};
    if (plan.enter === 'slam') {
      const s = clamp01((t - a) / 0.35);
      return {opacity: (t >= a ? 1 : 0) * gone, scale: 1 + 0.35 * (1 - enter(s)), each: undefined};
    }
    if (plan.enter === 'type') {
      const shown = Math.floor(u * total + 1e-6);
      return {opacity: gone, scale: 1, each: (i: number): [number, number] => [before[j] + i < shown ? 1 : 0, 0]};
    }
    return {opacity: (t >= a ? 1 : 0) * gone, scale: 1, each: undefined};
  };
};

/** One card's words: their line, its date and on a chapter their next line, entering as the style card's lines enter
 * (letter by letter rising, or fading, slamming, typed or cut on) and leaving over the exit before its print drops. */
export const CardWords: React.FC<{plan: Plan; card: Card; fonts: Fonts; t: number; index: number}> = ({plan, card: c, fonts, t, index}) => {
  if (t < c.titleAt || t >= c.leave) return null;
  const z = c.lift + 10;
  // the label's words ride the print from its station, so they land on it as it lifts toward the lens
  const on = onPrint(plan, c, index, t);
  const at = (ln: Line, scale: number) => on.clone().multiply(frameOf(plan, ln, z, 1, scale));
  const out = c.leave - plan.exit;
  const restLen = Math.min(plan.letters, 0.04 * c.rest.reduce((s, ln) => s + ln.text.length, 0));
  const rise = plan.enter === 'rise';
  const block = (lines: Line[], a: number, len: number) => {
    if (rise) {
      const each = lettersOf(plan, lines, t, a, len, out);
      return (j: number) => ({opacity: 1, scale: 1, each: each(j)});
    }
    return standing(plan, lines, t, a, len, out);
  };
  const title = block(c.title, c.titleAt, c.land - c.titleAt);
  const date = block([c.date], c.titleAt + 0.1, 0.45);
  const rest = block(c.rest, c.restAt, restLen);
  const label = (ln: Line, s: ReturnType<typeof title>, key: string) => (
    <Type3D key={key} font={fontOf(fonts, ln)} text={ln.text} color={colorOf(plan, ln.color)} anchor={ln.anchor} opacity={s.opacity}
      matrix={at(ln, s.scale)} each={s.each} shadow={shadowOf(ln)} renderOrder={1010 + index} />
  );
  return (
    <group>
      {c.title.map((ln, j) => {
        const s = title(j);
        return (
          <Type3D key={`t${j}`} font={fontOf(fonts, ln)} text={ln.text} color={colorOf(plan, ln.color)} side={plan.colors.ink} depth={DEPTH}
            anchor={ln.anchor} opacity={s.opacity} matrix={at(ln, s.scale)} each={s.each} shadow={shadowOf(ln)} renderOrder={1000 + index} />
        );
      })}
      {label(c.date, date(0), 'd')}
      {c.rest.map((ln, j) => label(ln, rest(j), `r${j}`))}
    </group>
  );
};

/** The closer's lines (the two dates, and the ask) on the wall, each entering letter by letter on the beat the board
 * gives it, and holding. */
export const CloserWords: React.FC<{plan: Plan; fonts: Fonts; t: number}> = ({plan, fonts, t}) => (
  <group>
    {plan.closer.lines.map((ln, i) => (t < (ln.at ?? 0) ? null : (
      <Type3D key={i} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, ln.color)} anchor={ln.anchor}
        matrix={frameOf(plan, ln, 1.2)} each={lettersOf(plan, [ln], t, ln.at ?? 0, ln.name === 'call' ? plan.letters : 0.5, null)(0)}
        shadow={PAPER_SHADOW} renderOrder={1500} />
    )))}
  </group>
);
