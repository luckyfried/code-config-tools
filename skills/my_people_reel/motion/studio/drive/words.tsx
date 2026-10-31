// The drive film's type in the camera's space: the hook's handle and year, and its title falling onto the edge; each
// person's stamp of where and when landing on their edge and their own words rising over it, the stamp then moving
// into its place under their slice on the closer's wall; and the closer's own lines. Every line that rises enters a
// word at a time on the kit's entry curve, its letters closing onto the line's tracking as each word lands, settled
// inside a second; a person's words that run onto several lines enter as one sentence, word after word in reading
// order down the lines.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, mixPt, span} from '../../system/three/motion';
import {Type3D, type Type3DProps} from '../../system/three/Type3D';
import {fileOf, layout, type Font} from '../../system/three/type';
import {timesOf, typeZ} from './card';
import {placeOnWall, WALL, type Card, type Line, type Placed, type Plan} from './plan';

const DEPTH = 0.11;
/** The share of a line's entry between one word's start and the next one's, and how far apart, in em, a word's letters
 * start before they close onto the line's tracking. */
const STAGGER = 0.16;
const OPEN = 0.1;

/** Beats a line of `text` takes to enter: longer for more words, never past a second; typed, longer for more letters,
 * never past 1.1 s. */
const entryBeats = (plan: Plan, text: string, say = 'rise') =>
  (say === 'type' ? Math.min(1.1, 0.25 + 0.025 * unitsOf(text, say)) : Math.min(0.95, 0.4 + 0.07 * text.trim().split(/\s+/u).length)) / plan.beat;

/** How a line's units enter: `rise` through the line's window, `slam` down from oversize onto the line, `type` struck
 * on whole one letter after another. */
export type Say = 'rise' | 'slam' | 'type';
/** The units a line of `text` enters in, as `say` names: its letters when typed, else its words. */
export const unitsOf = (text: string, say: string) => (say === 'type' ? text.replace(/\s/gu, '').length : text.trim().split(/\s+/u).length);

/** A line entering a unit at a time: `u` runs from 0 to 1 over its entry, and each unit, a share behind the one before,
 * enters on `enter` as `say` names; a rising word's letters close from open onto the line's tracking. A line that is
 * part of a longer sentence starts at its `first` unit of the sentence's `total`. */
const Rising: React.FC<Omit<Type3DProps, 'rise'> & {u: number; enter: (x: number) => number; first?: number; total?: number; say?: string}> = ({u, enter, first = 0, total, say = 'rise', font, text, tracking = 0, anchor, matrix, ...rest}) => {
  const words = useMemo(() => {
    const lay = layout(font, text, tracking);
    const shift = anchor === 'end' ? -lay.width : anchor === 'middle' ? -lay.width / 2 : 0;
    const out: {text: string; x: number; to: number}[] = [];
    let gap = true;
    for (const g of lay.glyphs) {
      const blank = /\s/u.test(g.char);
      if (out.length && !out[out.length - 1].to && (blank || say === 'type')) out[out.length - 1].to = g.x + shift;
      if (!blank && (gap || say === 'type')) out.push({text: '', x: g.x + shift, to: 0});
      if (!blank) out[out.length - 1].text += g.char;
      gap = blank;
    }
    if (out.length && !out[out.length - 1].to) out[out.length - 1].to = lay.width + shift;
    return out;
  }, [font, text, tracking, anchor, say]);
  if (u <= 0) return null;
  const n = total ?? words.length;
  if (say === 'type') {
    // a letter is struck whole the moment its turn comes, evenly through the entry
    const shown = Math.floor(u * n + 1e-6) - first;
    return (
      <group>
        {words.slice(0, Math.max(0, shown)).map((w, i) => (
          <Type3D key={i} {...rest} font={font} text={w.text} tracking={tracking} matrix={matrix.clone().multiply(new THREE.Matrix4().makeTranslation(w.x, 0, 0))} rise={1} />
        ))}
      </group>
    );
  }
  const g = n > 1 ? Math.min(STAGGER, 0.6 / (n - 1)) : 0;
  const d = 1 - (n - 1) * g;
  return (
    <group>
      {words.map((w, i) => {
        if (say === 'slam') {
          // a word drops from oversize onto its place and hits, whole
          const x = clamp01((u - (first + i) * g) / Math.min(d, 0.3));
          if (x <= 0) return null;
          const k = 1 + 0.6 * (1 - bezier([0.7, 0, 0.84, 0])(x));
          const mid = (w.to - w.x) / 2;
          const m = matrix.clone().multiply(new THREE.Matrix4().makeTranslation(w.x + mid, 0.35, 0)).multiply(new THREE.Matrix4().makeScale(k, k, k))
            .multiply(new THREE.Matrix4().makeTranslation(-mid, -0.35, 0));
          return <Type3D key={i} {...rest} font={font} text={w.text} tracking={tracking} matrix={m} rise={1} opacity={(rest.opacity ?? 1) * Math.min(1, x * 4)} />;
        }
        const e = enter(clamp01((u - (first + i) * g) / d));
        if (e <= 0) return null;
        const m = matrix.clone().multiply(new THREE.Matrix4().makeTranslation(w.x, 0, 0));
        return <Type3D key={i} {...rest} font={font} text={w.text} tracking={tracking + OPEN * (1 - e)} matrix={m} rise={Math.min(1, e)} />;
      })}
    </group>
  );
};

/** A line's baseline frame in world space: placed on the wall at depth `z`, tipped back by `tip` about its baseline, its extrusion scaled by `deep`. */
export const frameOf = (plan: Plan, p: Placed, z: number, deep = 1, tip = 0, scale = 1) => {
  const m = new THREE.Matrix4().makeTranslation(p.at[0] - plan.W / 2, plan.H / 2 - p.at[1], z);
  m.multiply(new THREE.Matrix4().makeRotationZ((-p.deg * Math.PI) / 180));
  if (tip) m.multiply(new THREE.Matrix4().makeRotationX(tip));
  m.multiply(new THREE.Matrix4().makeScale(p.size * scale, p.size * scale, p.size * scale * deep));
  return m;
};

const mixPlaced = (a: Placed, b: Placed, u: number): Placed => ({at: mixPt(a.at, b.at, u), deg: lerp(a.deg, b.deg, u), size: a.size * Math.pow(b.size / a.size, u)});

export type Fonts = Map<string, Font>;
export const fontOf = (fonts: Fonts, ln: {file?: string; face?: string; weight?: number}) => fonts.get(fileOf(ln))!;
export const colorOf = (plan: Plan, name?: string) => plan.colors[name ?? 'ink'] ?? name ?? plan.colors.ink;
const sideOf = (plan: Plan, name?: string) => (colorOf(plan, name) === plan.colors.accent ? plan.colors.ink : plan.colors.accent);
/** A line's color as it moves from its card (`a`) to its place on the wall (`b`), `u` of the way. */
const toward = (plan: Plan, a?: string, b?: string, u = 0) => '#' + new THREE.Color(colorOf(plan, a)).lerp(new THREE.Color(colorOf(plan, b ?? a)), u).getHexString();
/** The sides of a stamp standing over a photograph: its own color in shadow, so the orange stays the tag's. */
const shadeOf = (plan: Plan, name?: string) => '#' + new THREE.Color(colorOf(plan, name)).lerp(new THREE.Color('#000000'), 0.5).getHexString();

/** The thin strip a line stands on over a busy picture, in the line's own frame (em units, y up), wiping in from its
 * start as the line rises. */
const Strip: React.FC<{plan: Plan; ln: Line; matrix: THREE.Matrix4; rise: number; opacity: number; renderOrder: number}> = ({plan, ln, matrix, rise, opacity, renderOrder}) => {
  if (!ln.strip || opacity <= 0.002 || rise <= 0.002) return null;
  const w = ln.strip / ln.size + 0.5;
  const ground = colorOf(plan, ln.color) === plan.colors.paper ? plan.colors.ink : plan.colors.paper;
  return (
    <group matrixAutoUpdate={false} matrix={matrix}>
      <mesh position={[-0.25 + (w * rise) / 2, 0.3, -0.01]} scale={[w * rise, 1.22, 1]} renderOrder={renderOrder}>
        <planeGeometry args={[1, 1]} />
        <meshBasicMaterial color={ground} toneMapped={false} transparent opacity={0.94 * opacity} depthWrite={false} />
      </mesh>
    </group>
  );
};

/** One person's stamp and words. */
export const CardWords: React.FC<{plan: Plan; card: Card; fonts: Fonts; t: number; index: number}> = ({plan, card: c, fonts, t, index}) => {
  if (!c.stamp || t < c.cut) return null;
  const enter = bezier(plan.ease.enter);
  const s = c.T.s;
  const zt = typeZ(c);
  const onPhoto = c.field === 'photo';
  const D = (plan.H * s) / 2 / Math.tan((30 * Math.PI) / 360);
  // how the stamp lands, as the beat's move draws it: falling from the lens onto the edge (rise and underline), burned
  // on and blinking in the accent like a camcorder's date (date), slammed down from oversize (slam), or closing from
  // wide-set letters onto its tracking (stretch)
  const how = c.words;
  const k = t - c.cut;
  const falls = how === 'rise' || how === 'underline';
  const land = falls ? span(t, c.cut, 0.5, bezier([0.15, 0.85, 0.3, 1])) : 1;
  const pop = falls ? enter(Math.min(1, k / 0.55)) : 1;
  const slam = how === 'slam' ? 1 + 0.7 * (1 - bezier([0.7, 0, 0.84, 0])(clamp01(k / 0.3))) : 1;
  const blink = how === 'date' ? (k < 0.12 || (k >= 0.24 && k < 0.36) ? 1 : k < 0.36 ? 0 : 1) : 1;
  const open = how === 'stretch' ? 0.9 * (1 - bezier([0.2, 0.9, 0.3, 1])(clamp01(k / 0.6))) : 0;
  // the stamp and the carried words are in their places on the wall by the frame of the cut, with the card
  const [leaveAt, leaveFor] = timesOf(c).leave;
  const leave = span(t, leaveAt, leaveFor);
  const edge = placeOnWall(c.T, c.stamp);
  const slot = c.slotStamp ? placeOnWall(WALL, c.slotStamp) : edge;
  const p = mixPlaced(edge, slot, c.slotStamp ? leave : 0);
  const z = lerp(zt, 0.6, leave) + (1 - land) * D * 0.55;
  const order = 1000 + index * 10;
  // the words enter as one sentence: each line from its first word's place in it
  const counts = c.rest.map((ln) => unitsOf(ln.text, c.say));
  const total = counts.reduce((a, b) => a + b, 0);
  const u = clamp01((t - c.restAt) / entryBeats(plan, c.rest.map((ln) => ln.text).join(' '), c.say));
  const lines = c.rest.map((ln, i) => {
    const carried = c.slotRest[ln.name ?? ''];
    const from = placeOnWall(c.T, ln);
    const pl = carried ? mixPlaced(from, placeOnWall(WALL, carried), leave) : from;
    const fade = carried ? 1 : 1 - span(t, c.go, 0.3);
    const color = toward(plan, ln.color, carried?.color, leave);
    const lit = onPhoto && !ln.strip && colorOf(plan, ln.color) === plan.colors.paper ? 0.4 * (1 - leave) : 0;
    const m = frameOf(plan, pl, lerp(zt, 1.0, leave));
    return (
      <group key={i}>
        <Strip plan={plan} ln={ln} matrix={m} rise={Math.min(1, enter(u))} opacity={fade * (1 - leave)} renderOrder={order + 4} />
        <Rising u={u} enter={enter} say={c.say} first={counts.slice(0, i).reduce((a, b) => a + b, 0)} total={total} font={fontOf(fonts, ln)} text={ln.text}
          tracking={ln.tracking} color={color} anchor={carried && leave >= 0.5 ? carried.anchor : ln.anchor} matrix={m} opacity={fade} shadow={lit} renderOrder={order + 5} />
      </group>
    );
  });
  const stampColor = how === 'date' && leave < 1 ? plan.colors.accent : toward(plan, c.stamp.color, c.slotStamp?.color, leave);
  const sm = frameOf(plan, p, z, lerp(1, 0.35, leave), (1 - land) * -1.25, Math.max(0.2, pop) * slam);
  // the underline: a stroke of the accent drawn on under the stamp from its start as it lands
  const font = fontOf(fonts, c.stamp);
  const width = layout(font, c.stamp.text, c.stamp.tracking ?? 0).width;
  const lead = c.stamp.anchor === 'end' ? -width : c.stamp.anchor === 'middle' ? -width / 2 : 0;
  const drawn = how === 'underline' ? bezier([0.4, 0, 0.2, 1])(clamp01((k - 0.25) / 0.45)) * (1 - leave) : 0;
  return (
    <group>
      <Type3D font={font} text={c.stamp.text} tracking={(c.stamp.tracking ?? 0) + open} anchor={c.slotStamp && leave >= 0.5 ? c.slotStamp.anchor : c.stamp.anchor}
        color={stampColor}
        side={onPhoto ? shadeOf(plan, c.stamp.color) : sideOf(plan, c.stamp.color)}
        matrix={sm} depth={DEPTH}
        opacity={(c.slotStamp ? 1 : 1 - leave) * blink} shadow={(onPhoto ? 0.4 : 0.16) * land * (1 - leave)}
        castShadow={z > 4} renderOrder={order} />
      {drawn > 0.002 ? (
        <group matrixAutoUpdate={false} matrix={sm}>
          <mesh position={[lead + (width * drawn) / 2, -0.16, 0.02]} scale={[width * drawn, 0.07, 1]} renderOrder={order + 1}>
            <planeGeometry args={[1, 1]} />
            <meshBasicMaterial color={plan.colors.accent} toneMapped={false} transparent depthWrite={false} />
          </mesh>
        </group>
      ) : null}
      {lines}
    </group>
  );
};

/** The hook's words: the handle and the year rising as the blade opens the photograph, then the title falling from
 * the lens onto the edge a line at a time, all of it going as the camera leaves with the tag. */
export const HookWords: React.FC<{plan: Plan; fonts: Fonts; t: number}> = ({plan, fonts, t}) => {
  const hook = plan.cards[0];
  const enter = bezier(plan.ease.enter);
  const s = hook.T.s;
  const z = typeZ(hook);
  const onPhoto = hook.field === 'photo';
  const D = (plan.H * s) / 2 / Math.tan((30 * Math.PI) / 360);
  const gone = 1 - span(t, hook.go, 0.35);
  if (gone <= 0) return null;
  const kick = plan.kicker.map((ln, i) => {
    const u = clamp01((t - (0.05 + i * 0.15)) / entryBeats(plan, ln.text));
    const m = frameOf(plan, placeOnWall(hook.T, ln), z);
    const lit = onPhoto && !ln.strip && colorOf(plan, ln.color) === plan.colors.paper ? 0.4 : 0;
    return (
      <group key={`k${i}`}>
        <Strip plan={plan} ln={ln} matrix={m} rise={Math.min(1, enter(u))} opacity={gone} renderOrder={1004} />
        <Rising u={u} enter={enter} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, ln.color)}
          anchor={ln.anchor} matrix={m} opacity={gone} shadow={lit} renderOrder={1005} />
      </group>
    );
  });
  // the title's lines fall onto the edge, the lower one (standing on it) first
  const title = [...plan.title].reverse().map((ln, i) => {
    const at = plan.titleAt + i * 0.12;
    if (t < at) return null;
    const land = span(t, at, 0.45, bezier([0.15, 0.85, 0.3, 1]));
    const pop = enter(Math.min(1, (t - at) / 0.5));
    return (
      <Type3D key={`t${i}`} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} anchor={ln.anchor} color={colorOf(plan, ln.color)} side={onPhoto ? shadeOf(plan, ln.color) : sideOf(plan, ln.color)}
        matrix={frameOf(plan, placeOnWall(hook.T, ln), z + (1 - land) * D * 0.5, 1, (1 - land) * -1.2, Math.max(0.2, pop))}
        depth={DEPTH} opacity={gone} shadow={(onPhoto ? 0.4 : 0.16) * land} castShadow renderOrder={1010 + i} />
    );
  });
  return <group>{kick}{title}</group>;
};

/** The closer's own lines (the handle and the title), rising onto the wall as the tag lands on the last, settled as the wall stands whole. */
export const CloserWords: React.FC<{plan: Plan; fonts: Fonts; t: number}> = ({plan, fonts, t}) => {
  const enter = bezier(plan.ease.enter);
  const n = plan.closer.lines.length;
  // each line settled a little before the next, the last of them as the wall stands whole
  const at = (i: number, ln: Line) => plan.closer.walled - 0.15 - 0.1 * (n - 1 - i) - entryBeats(plan, ln.text);
  return (
    <group>
      {plan.closer.lines.map((ln, i) => (
        <Rising key={i} u={clamp01((t - at(i, ln)) / entryBeats(plan, ln.text))} enter={enter} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking}
          color={colorOf(plan, ln.color)} anchor={ln.anchor} matrix={frameOf(plan, placeOnWall(WALL, ln), 1.2)} renderOrder={1500} />
      ))}
    </group>
  );
};
