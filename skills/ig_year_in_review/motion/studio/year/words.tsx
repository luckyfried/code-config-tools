// The year film's type in the camera's space: the year slamming onto the line the dot draws, each month's name and
// their own line from the post where the card's photo layout sets them, coming on the card's way and sinking away as
// the month is left, the row's own name as the line lands in it, and the closer's own lines. A month's words stand in
// the card's colors on the plate the board measured under them, on the photograph's near layer, so they move with the
// photograph; the wall's type stands on the plate the board measured under it, which holds it at the board's contrast
// over the ground.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, span, type Pt} from '../../system/three/motion';
import {Type3D, type Enter} from '../../system/three/Type3D';
import {fileOf, type Font} from '../../system/three/type';
import {headingSeen} from './camera';
import {quad, setBox, setQuad, softBox, WHOLE} from './month';
import {baseline, layerOf, onWall, placeOnWall, WALL, type Line, type Month, type Placed, type Plan, type Xf} from './plan';

const DEPTH = 0.11;

/** A line's baseline frame in world space: placed on the wall at depth `z`, tipped back by `tip` about its baseline, its extrusion scaled by `deep`. */
export const frameOf = (plan: Plan, p: Placed, z: number, deep = 1, tip = 0, scale = 1) => {
  const m = new THREE.Matrix4().makeTranslation(p.at[0] - plan.W / 2, plan.H / 2 - p.at[1], z);
  m.multiply(new THREE.Matrix4().makeRotationZ((-p.deg * Math.PI) / 180));
  if (tip) m.multiply(new THREE.Matrix4().makeRotationX(tip));
  m.multiply(new THREE.Matrix4().makeScale(p.size * scale, p.size * scale, p.size * scale * deep));
  return m;
};

export type Fonts = Map<string, Font>;
const fontOf = (fonts: Fonts, ln: Line) => fonts.get(fileOf(ln))!;
const colorOf = (plan: Plan, name?: string) => plan.colors[name ?? 'ink'] ?? name ?? plan.colors.ink;
// paper on a photograph carries a soft ink shadow over its plate; ink stands on its plate alone
const shadeOf = (name?: string) => (name === 'paper' ? 0.45 : 0);
const sideOf = (plan: Plan, name?: string) => (colorOf(plan, name) === plan.colors.accent ? plan.colors.ink : plan.colors.accent);

/** The beat word k of n of a month's line rises on: the first at t0 and the last at t0 + len, fast at first and
 * settling. */
export const wordAt = (t0: number, len: number, k: number, n: number) => t0 + (n > 1 ? len * (1 - Math.sqrt(1 - k / (n - 1))) : 0);

const rising = (plan: Plan, t: number, at: number, len = 0.4) => Math.min(1, bezier(plan.ease.enter)(Math.min(1, Math.max(0, (t - at) / len))));

/** A line entering letter by letter from beat `at` over `len` beats, its letters closing in from a little apart. */
const entering = (plan: Plan, t: number, at: number, len: number): Enter => ({at: clamp01((t - at) / len), curve: bezier(plan.ease.enter), track: 0.035});

/** How a month's words come on from beat `at` over `len` beats, the card's way: `type` letter by letter as a typewriter
 * sets them, `rise` each letter rising through its baseline, `slam` down from oversize onto its place, `fade` in, `cut`
 * at once. */
const entranceOf = (plan: Plan, t: number, at: number, len: number): {enter?: Enter; scale: number; opacity: number} => {
  const u = clamp01((t - at) / len);
  const on = t >= at ? 1 : 0;
  switch (plan.photo.line.enter) {
    case 'type':
      return {enter: {at: clamp01((t - at) / (2.5 * len)), curve: (e) => (e > 0 ? 1 : 0), track: 0}, scale: 1, opacity: on};
    case 'slam':
      return {scale: 1 + 0.4 * (1 - bezier([0.25, 0.9, 0.35, 1.2])(u)), opacity: on};
    case 'fade':
      return {scale: 1, opacity: bezier(plan.ease.enter)(u)};
    case 'cut':
      return {scale: 1, opacity: on};
    default:
      return {enter: entering(plan, t, at, len), scale: 1, opacity: 1};
  }
};

/** The lines every Type3D in the film draws, for the fonts to load. */
export const linesOf = (plan: Plan): Line[] => [
  plan.title, ...(plan.handle ? [plan.handle] : []), plan.signoff,
  ...plan.months.flatMap((m) => [m.name, ...m.said, m.row.label]),
];

/** How round a plate's corners are, px of its frame, and how far a wall plate's edge fades. */
const ROUND = 12;
const FADE = 2;

/** A plate: a soft box (piece or wall px, clockwise from the top left, mapped by `T`, `w` by `h` of its frame) at
 * height `z`, its edge fading over `soft`, in `color` at `alpha` times `shown`, blended over the photograph under it as
 * the board measured it. */
const PlateView: React.FC<{plan: Plan; pts: Pt[]; w: number; h: number; T: Xf; z: number; color: string; alpha: number; shown: number; renderOrder: number; soft?: number}> = (
  {plan, pts, w, h, T, z, color, alpha, shown, renderOrder, soft = FADE}) => {
  const q = useMemo(() => quad(softBox('#000000')), []);
  const mat = q.mesh.material as THREE.MeshBasicMaterial;
  mat.color.set(colorOf(plan, color));
  mat.opacity = alpha * shown;
  setBox(mat, w, h, Math.min(ROUND, soft), soft);
  setQuad(q, pts.map((p) => {
    const at = onWall(T, p);
    return new THREE.Vector3(at[0] - plan.W / 2, plan.H / 2 - at[1], z);
  }), WHOLE);
  q.mesh.visible = mat.opacity > 0.001;
  q.mesh.renderOrder = renderOrder;
  return <primitive object={q.mesh} />;
};

const corners = ([x0, y0, x1, y1]: number[]): Pt[] => [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];

/** A month's plate's corners in its piece frame, turned with its words about their pivot. */
const plateOf = (m: Month): Pt[] =>
  corners(m.plate.box).map(([x, y]) => baseline({text: '', x, y, size: 0, rotate: m.plate.rotate, pivot: m.plate.pivot}).at);

/** The plates under the wall's type: the year's as it slams in, the rows' names' as the dot reaches the rows, the handle's
 * and the sign-off's as the closer's lines come up. */
export const WallPlates: React.FC<{plan: Plan; t: number}> = ({plan, t}) => {
  const when: Record<string, {z: number; shown: number}> = {
    title: {z: 0.9, shown: span(t, plan.hook.slam[0], plan.hook.slam[1]) * headingSeen(plan, t)},
    labels: {z: 0.7, shown: rising(plan, t, plan.closer.hops[0] - 0.2, 0.25)},
    handle: {z: 1.1, shown: rising(plan, t, plan.closer.hops[0], 0.5)},
    signoff: {z: 1.1, shown: rising(plan, t, plan.closer.hops[0], 0.5)},
  };
  return (
    <group>
      {plan.plates.map((p, i) => (
        <PlateView key={p.of} plan={plan} pts={corners(p.box)} w={p.box[2] - p.box[0]} h={p.box[3] - p.box[1]} T={WALL}
          z={when[p.of].z} color={p.color} alpha={p.alpha} shown={t < plan.hook.slam[0] ? 0 : when[p.of].shown} renderOrder={990 + i} />
      ))}
    </group>
  );
};

/** How long a month's words take to sink back through its line, in beats from the moment the camera starts to leave it
 * (the last month's, from just before its halves close): they are gone before the next month's photograph starts to open
 * over them. */
const SINK = 0.3;


/** One month's name and their line, on their plate on the near layer: the name comes on the card's way as the
 * photograph opens, their words one by one under it, and all of them sink away as the camera leaves the month; the
 * month's row takes its own name as the line lands in it. */
export const MonthWords: React.FC<{plan: Plan; month: Month; fonts: Fonts; t: number; index: number}> = ({plan, month: m, fonts, t, index}) => {
  const a = m.at;
  if (t < a.open[0]) return null;
  const order = 1000 + index * 10;
  // the row's name rises in its row as the dot lands at the row's end in the closer
  const named = plan.closer.hops[index] - 0.2;
  const row = t >= named ? (
    <Type3D font={fontOf(fonts, m.row.label)} text={m.row.label.text} tracking={m.row.label.tracking} color={colorOf(plan, m.row.label.color)}
      side={sideOf(plan, m.row.label.color)} matrix={frameOf(plan, placeOnWall(WALL, m.row.label), 0.8, 0.3)} depth={lifted(plan) ? DEPTH * 0.6 : 0}
      enter={entering(plan, t, named, 0.4)} renderOrder={order + 2} />
  ) : null;
  // a month's words sink as the camera leaves its photograph; the last month's hold while the camera pulls back to the
  // wall and sink as its halves close onto the line. With no photograph the words are the whole frame: they hold to the
  // month's end, and the last month's to the moment its line slides into its row, so no beat shows an empty ground
  const last = index === plan.months.length - 1;
  const bare = m.picture === null;
  const leave = last ? (bare ? a.slide[0] : a.fold[0]) - SINK : bare ? a.end - SINK : a.pull[0];
  if (t >= leave + SINK) return row;
  const s = m.T.s;
  const layer = layerOf(plan, m, t);
  const z = layer.z + 7 * s;
  // everything on the photograph sinks as the camera starts to leave it
  const sink = 1 - span(t, leave, SINK, bezier([0.45, 0, 0.3, 1]));
  const n = m.said.length;
  const shown = Math.min(sink, rising(plan, t, a.part[0]));
  // a typewriter sets the line's letters one after another across its words, at one pace; every other way brings the
  // words on one by one
  const typed = plan.photo.line.enter === 'type';
  // the typewriter's whole run, from the line's beat to the moment it stands whole, spread over its letters
  const pace = (a.say[1] + 0.2) / m.said.reduce((c, ln) => c + ln.text.length + 1, -1);
  let before = 0;
  const words = m.said.map((ln, k) => {
    const from = before;
    before += ln.text.length + 1;
    const at = typed ? a.say[0] + pace * from - 0.05 : wordAt(a.say[0], a.say[1], k, n) - 0.05;
    const e = entranceOf(plan, t, at, typed ? (pace * ln.text.length) / 2.5 : 0.2);
    return t >= at ? (
      <Type3D key={k} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, ln.color)}
        matrix={frameOf(plan, placeOnWall(layer.T, ln), z, 1, 0, e.scale)} rise={sink} opacity={sink * e.opacity} enter={e.enter}
        shadow={shadeOf(ln.color)} renderOrder={order + 4} />
    ) : null;
  });
  const ne = entranceOf(plan, t, a.part[0], 0.35);
  return (
    <group>
      <PlateView plan={plan} pts={plateOf(m)} w={m.plate.box[2] - m.plate.box[0]} h={m.plate.box[3] - m.plate.box[1]} T={layer.T}
        z={layer.z + 3 * s} color={m.plate.color} alpha={m.plate.alpha} shown={shown} renderOrder={order + 1} soft={m.plate.soft} />
      <Type3D font={fontOf(fonts, m.name)} text={m.name.text} tracking={m.name.tracking} color={colorOf(plan, m.name.color)}
        matrix={frameOf(plan, placeOnWall(layer.T, m.name), z, 1, 0, ne.scale)} rise={sink} opacity={sink * ne.opacity} enter={ne.enter}
        shadow={shadeOf(m.name.color)} renderOrder={order + 2} />
      {words}
      {row}
    </group>
  );
};

/** Whether the wall's type stands up off a photograph, with depth and a shadow; on a card's flat ground it is printed
 * flat, the way the card sets its words on paper. */
const lifted = (plan: Plan) => plan.ground.flat === null;

/** The hook's words: the year enters on the underline the dot draws the way the card brings its line on, and stays,
 * shown only while wholly in the picture. */
export const HookWords: React.FC<{plan: Plan; fonts: Fonts; t: number}> = ({plan, fonts, t}) => {
  const [s0, sl] = plan.hook.slam;
  if (t < s0) return null;
  const e = entranceOf(plan, t, s0, sl);
  const up = lifted(plan) ? span(t, s0, sl, bezier([0.5, 0, 0.9, 0.5])) : 0;
  return (
    <Type3D font={fontOf(fonts, plan.title)} text={plan.title.text} tracking={plan.title.tracking} color={colorOf(plan, plan.title.color)} side={sideOf(plan, plan.title.color)}
      matrix={frameOf(plan, placeOnWall(WALL, plan.title), 1, 1, 0, e.scale)} depth={lifted(plan) ? DEPTH * 0.7 : 0} enter={e.enter}
      shadow={0.2 * up} opacity={headingSeen(plan, t) * e.opacity} castShadow={lifted(plan)} renderOrder={1001} />
  );
};

/** A line's full stop on the wall: on its baseline just past its last letter, in world space, with the radius of a full
 * stop at the line's size. */
export const stopAfter = (plan: Plan, fonts: Fonts, ln: Line) => {
  const p = placeOnWall(WALL, ln);
  const font = fontOf(fonts, ln);
  const width = font ? (font.stringToGlyphs(ln.text).reduce((w: number, g: any) => w + g.advanceWidth, 0) / font.unitsPerEm) * p.size : 0;
  const r = Math.max(6, 0.09 * p.size);
  const along = width + 0.06 * p.size + r;
  return {p: new THREE.Vector3(p.at[0] + along - plan.W / 2, plan.H / 2 - (p.at[1] - r), 2.5), r};
};

/** The closer's own lines, the handle and the sign-off: entering letter by letter from the dot's first landing, the
 * sign-off waiting for the dot that ends it. */
export const CloserWords: React.FC<{plan: Plan; fonts: Fonts; t: number}> = ({plan, fonts, t}) => {
  const at = plan.closer.hops[0];
  if (t < at) return null;
  return (
    <group>
      {[plan.handle, plan.signoff].filter((ln): ln is Line => ln !== null).map((ln, i) => (
        <Type3D key={i} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, ln.color)} anchor={ln.anchor}
          matrix={frameOf(plan, placeOnWall(WALL, ln), 1.2)} enter={entering(plan, t, at + 0.15 * i, 0.8)} renderOrder={1500} />
      ))}
    </group>
  );
};
