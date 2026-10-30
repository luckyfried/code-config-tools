// The places film's type: each stop's words in the camera's space on its card, where the style card's layout set them
// (the label in the label's face over the line in the line's face), entering the way the layout says (a cut, a fade,
// typed letter by letter, risen, or slammed onto the card) when the stop's words come up and leaving before the camera
// moves on; and the hook's title and handle over the whole route from the first frame, in the frame's own px. The
// closer's words are its shape's (closers.tsx).
import * as THREE from 'three';
import {bezier, span} from '../../system/three/motion';
import {Type3D} from '../../system/three/Type3D';
import {fileOf, type Font} from '../../system/three/type';
import type {System} from '../../system/types';
import {cardSpace} from './card';
import {colorOf, liftOf, placeOnWall, type Card, type Line, type Placed, type Plan} from './plan';

/** Beats before the camera leaves a place that its words begin to leave: they are gone before the card moves, so no
 * word rides a card through a move or stands over the map. */
const LEAVE = 0.35;
/** Beats the label leads the line by, and how long each entrance takes. */
const LEAD = 0.15;
const ENTER: Record<string, number> = {cut: 0, fade: 0.6, type: 0.9, rise: 0.5, slam: 0.4};

/** A line's baseline frame in world space: placed on the wall at depth `z`, scaled by `scale` about its baseline start. */
export const frameOf = (plan: Plan, p: Placed, z: number, scale = 1) => {
  const m = new THREE.Matrix4().makeTranslation(p.at[0] - plan.W / 2, plan.H / 2 - p.at[1], z);
  m.multiply(new THREE.Matrix4().makeRotationZ((-p.deg * Math.PI) / 180));
  m.multiply(new THREE.Matrix4().makeScale(p.size * scale, p.size * scale, p.size * scale));
  return m;
};

export type Fonts = Map<string, Font>;
const fontOf = (fonts: Fonts, ln: Line) => fonts.get(fileOf(ln))!;
const step = (u: number) => (u > 0 ? 1 : 0);

/** The share of a line's time on screen its entrance may take, so a short stop's words stand whole before they leave. */
const ENTER_SHARE = 0.5;

/** How a line stands at `age` beats after its entrance began and `left` beats into its exit, with `room` beats between
 * the two: its rise, opacity, scale, and the curve and stagger its letters rise on, by the layout's entrance. */
const entrance = (plan: Plan, enter: string, age: number, left: number, chars: number, room = Infinity) => {
  const inE = bezier(plan.ease.enter), outE = bezier(plan.ease.exit);
  const full = enter === 'type' ? Math.min(1.4, Math.max(0.5, chars * 0.035)) : ENTER[enter] ?? 0.5;
  const len = Math.min(full, Math.max(0, room) * ENTER_SHARE);
  const u = len > 0 ? Math.min(1, Math.max(0, age / len)) : age >= 0 ? 1 : 0;
  const out = enter === 'cut' ? step(left) : outE(Math.min(1, Math.max(0, left / 0.3)));
  if (enter === 'fade') return {rise: age >= 0 ? 1 : 0, opacity: inE(u) * (1 - out), scale: 1, stagger: 0, ease: inE};
  if (enter === 'type') return {rise: Math.min(u, 1 - out), opacity: 1, scale: 1, stagger: 0.97, ease: step};
  if (enter === 'slam') {
    const k = span(age, 0, len, bezier([0.2, 0, 0.1, 1]));
    return {rise: age >= 0 ? 1 : 0, opacity: Math.min(1, u * 3) * (1 - out), scale: 1 + 0.35 * (1 - k), stagger: 0, ease: inE};
  }
  if (enter === 'cut') return {rise: age >= 0 && out < 1 ? 1 : 0, opacity: 1, scale: 1, stagger: 0, ease: inE};
  return {rise: Math.min(u, 1 - out), opacity: 1, scale: 1, stagger: 0.3, ease: inE};
};

/** A color's luma, 0 to 1 (NaN for a value that is not a hex color). */
const lumaOf = (hex: string) => {
  const v = /^#[0-9a-f]{6}/i.test(hex) ? parseInt(hex.slice(1, 7), 16) : NaN;
  return (0.299 * ((v >> 16) & 255) + 0.587 * ((v >> 8) & 255) + 0.114 * (v & 255)) / 255;
};
/** Whether a color is light: its luma over 0.6. */
const light = (hex: string) => lumaOf(hex) > 0.6;
/** The halo a hook line carries over the map, so its letters read over land and water alike: the card's color furthest
 * in lightness from the line's own. */
const haloOf = (plan: Plan, fill: string) => {
  const tones = Object.values(plan.colors).filter((c) => typeof c === 'string' && Number.isFinite(lumaOf(c)));
  const by = tones.sort((a, b) => lumaOf(a) - lumaOf(b));
  return light(fill) ? by[0] : by[by.length - 1];
};
/** The halo's width, a share of the line's size: wider round the small handle than round the title's heavy letters. */
const HALO = {title: 0.07, other: 0.16};
/** The shadow a light line standing on the photograph carries, so a bright patch of the picture under it never takes
 * its letters. */
const ON_PHOTO_SHADOW = 0.85;

/** One stop's words on its card. */
export const CardWords: React.FC<{plan: Plan; card: Card; fonts: Fonts; t: number; index: number}> = ({plan, card: c, fonts, t, index}) => {
  const from = c.kind === 'hook' ? plan.hook.name : c.cutAt;
  const until = c.goAt - LEAVE;
  if (t < from || t > until + 0.35) return null;
  const k = cardSpace(plan, c, index, t);
  if (k.whole < 0.5) return null;
  const lift = liftOf(c);
  const enter = plan.layout.line.enter;
  return (
    <group>
      {c.lines.map((ln, i) => {
        const lead = ln.name === 'label' ? 0 : LEAD + 0.08 * Math.max(0, i - 1);
        const e = entrance(plan, enter, t - from - lead, t - until, ln.text.length, until - from - lead);
        if (e.rise <= 0 || e.opacity <= 0.001) return null;
        const p = placeOnWall(c.T, ln);
        const color = colorOf(plan, ln.color);
        const [x0, y0, x1, y1] = c.box;
        const onPhoto = ln.y > y0 && ln.y - ln.size < y1 && ln.x < x1 && ln.x > x0 - ln.size;
        return (
          <Type3D key={i} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={color} anchor={ln.anchor}
            matrix={frameOf(plan, p, lift + 2 * c.s, e.scale)} rise={e.rise} stagger={e.stagger} ease={e.ease} opacity={e.opacity}
            shadow={onPhoto && light(color) ? ON_PHOTO_SHADOW : 0} renderOrder={1000 + index * 10 + i} />
        );
      })}
    </group>
  );
};

/** The face a line is set in, for the frame's own type: the display face's family when it is set in its file. */
const familyOf = (system: System, ln: Line) => (ln.file === system.display.file ? system.display.family : system.text.family);

/** The hook's title and handle over the whole route, entering in the card's way from the first frame (the handle a
 * little after the title) and leaving as the camera dives onto the first place. They are set in the frame's px, so the
 * dive never moves them. */
export const HookTitle: React.FC<{plan: Plan; system: System; t: number}> = ({plan, system, t}) => {
  const {dive} = plan.hook;
  const mode = plan.layout.line.enter;
  const out = mode === 'cut' ? (t < dive ? 0 : 1) : span(t, dive - 0.25, 0.4, bezier(plan.ease.exit));
  if (out >= 0.999) return null;
  const enter = bezier(plan.ease.enter);
  return (
    <svg width={plan.W} height={plan.H} style={{position: 'absolute', left: 0, top: 0, opacity: 1 - out}}>
      {plan.hook.kicker.map((ln, i) => {
        const [cx, cy] = ln.pivot ?? [ln.x, ln.y];
        const u = span(t, i * TITLE_STEP, TITLE_IN, enter);
        const text = mode === 'type' ? ln.text.slice(0, Math.ceil(ln.text.length * span(t, i * TITLE_STEP, TITLE_IN))) : ln.text;
        const a = mode === 'fade' || mode === 'rise' ? u : mode === 'cut' || mode === 'type' ? (t >= i * TITLE_STEP ? 1 : 0) : Math.min(1, u * 3);
        const lift = mode === 'rise' ? (1 - u) * ln.size * 0.5 : 0;
        const k = mode === 'slam' ? 1 + 0.35 * (1 - u) : 1;
        const moves = [ln.rotate ? `rotate(${ln.rotate} ${cx} ${cy})` : '', lift ? `translate(0 ${lift})` : '',
          k !== 1 ? `translate(${cx} ${cy}) scale(${k}) translate(${-cx} ${-cy})` : ''].filter(Boolean).join(' ');
        const fill = colorOf(plan, ln.color);
        return (
          <text key={i} x={ln.x} y={ln.y} fontFamily={`'${familyOf(system, ln)}'`} fontSize={ln.size} fill={fill}
            stroke={haloOf(plan, fill)} strokeWidth={ln.size * (ln.name === 'title' ? HALO.title : HALO.other)} strokeOpacity={0.8}
            strokeLinejoin="round" paintOrder="stroke"
            letterSpacing={`${ln.tracking ?? 0}em`} textAnchor={ln.anchor} transform={moves || undefined} opacity={a}
            style={{fontVariationSettings: 'normal'}}>{text}</text>
        );
      })}
    </svg>
  );
};

/** Beats after the title that the handle enters, and the beats each takes to come in. */
const TITLE_STEP = 0.35;
const TITLE_IN = 0.55;

