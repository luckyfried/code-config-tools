// The reel's type in the camera's space: the month's line over the first photograph, each moment's day and place and
// their own words on the field under its print, LEAD card px in front of the print, and the closer's words and the day
// under each of its photographs. Every line lands word by word, each word rising up its baseline with its letters
// spaced out and closing as it lands, and leaves in reverse: last word first, each sinking back below its baseline as
// its letters open, never wider than the space beside it.
import * as THREE from 'three';
import {bezier, clamp01, type Pt} from '../../system/three/motion';
import {closerOf} from '../../system/moves/index';
import {Type3D} from '../../system/three/Type3D';
import {fileOf, layout, shownAt, type Font} from '../../system/three/type';
import {DAY_DEPTH, distOf, LEAD, WALL_T, onWall, risenAt, standOutAt, stateAt, type Line, type Reel, type Xf} from './plan';

type Fonts = Map<string, Font>;
/** The closer's words stand this far off the wall, in front of the dust drifting over it. */
const WORDS_Z = 16;
const enter = bezier([0.22, 1.2, 0.36, 1]);
const leave = bezier([0.5, 0, 0.75, 0.6]);
/** How far a word's letters stand apart as it starts to land, em, at most: a long word opens less, so it never spreads
 * past the space between it and the next. */
const OPEN = 0.18;
const ROOM = 0.4;

export const linesOf = (r: Reel): Line[] => [...r.cards.flatMap((c) => c.lines), ...r.closer.lines, ...r.closer.tiles.map((x) => x.label)];

/** A baseline frame in world space: start (x, y) on the wall at depth z, one em `size` px, its extrusion scaled by `deep`, tipped back by `tip`. */
export const frameOf = (r: {W: number; H: number}, x: number, y: number, size: number, z: number, deep = 1, tip = 0) => {
  const m = new THREE.Matrix4().makeTranslation(x - r.W / 2, r.H / 2 - y, z);
  if (tip) m.multiply(new THREE.Matrix4().makeRotationX(tip));
  return m.multiply(new THREE.Matrix4().makeScale(size, size, size * deep));
};

const colorOf = (r: Reel, name?: string) => r.colors[name ?? 'ink'] ?? name ?? r.colors.ink;
const fontOf = (fonts: Fonts, ln: Line) => fonts.get(fileOf(ln))!;

/** One line set on a frame `T` of the wall, landing word by word from `at` and gone in reverse from `out`: each word
 * rises up its baseline with its letters apart, closing as it lands, and sinks back the same way, the last word first.
 * A count lands whole, since it counts. `about` scales the line's place and size about a point of the wall ([x, y, k]),
 * so a line standing in front of a card's print lands where the board placed it as seen from the card's station. */
const Set: React.FC<{r: Reel; fonts: Fonts; ln: Line; T: Xf; z: number; t: number; at: number; out?: number; shadow?: number; order: number; about?: [number, number, number]}> = ({r, fonts, ln, T, z, t, at, out, shadow = 0, order, about = [0, 0, 1]}) => {
  if (t < at) return null;
  const font = fontOf(fonts, ln);
  const text = shownAt(ln, t);
  const words = ln.tally ? [{text, i: 0}] : [...text.matchAll(/\S+/g)].map((m) => ({text: m[0], i: m.index ?? 0}));
  const step = ln.step ?? r.enter.step;
  const [mx, my, k] = about;
  const place = (p: Pt): Pt => [mx + (p[0] - mx) * k, my + (p[1] - my) * k];
  const [x, y] = onWall(T, [ln.x, ln.y]);
  // the card's tracking for the face, em, between every letter; a landing word opens its letters further on top of it
  const base = ln.tracking ?? 0;
  const full = layout(font, text, base).width;
  const shift = ln.anchor === 'end' ? -full : ln.anchor === 'middle' ? -full / 2 : 0;
  return (
    <group>
      {words.map((w, j) => {
        // landing, it runs a little past its place and settles back; leaving, it drops away, the last word first
        const gone = out === undefined ? 0 : leave(clamp01((t - out - (words.length - 1 - j) * step * 0.6) / 0.3));
        const p = enter(clamp01((t - at - j * step) / r.enter.beats)) * (1 - gone);
        if (p <= 0) return null;
        const n = [...w.text].length;
        const track = Math.min(OPEN, ROOM / Math.max(1, n - 1)) * (1 - Math.min(1, p));
        const dx = (shift + layout(font, text.slice(0, w.i), base).width - (track * (n - 1)) / 2) * ln.size * T.s;
        const [px, py] = place([x + dx, y]);
        return (
          <Type3D key={j} font={font} text={w.text} tracking={base + track} color={colorOf(r, ln.color)} matrix={frameOf(r, px, py, ln.size * T.s * k, z)}
            rise={Math.min(1, p)} shadow={shadow} shade={r.colors.ink} renderOrder={order} />
        );
      })}
    </group>
  );
};

/** The month's line over the first photograph, and each moment's day and place and their words on the field under its
 * print, each line landing from its `at` and gone from its `out`, before the camera leaves. */
export const PostWords: React.FC<{reel: Reel; fonts: Fonts; t: number}> = ({reel: r, fonts, t}) => {
  const k = 1 - LEAD / distOf(r);
  return (
    <group>
      {r.cards.map((c, i) => (t > c.move[0] + 0.2 ? null : c.lines.map((ln, j) => (
        <Set key={`${c.key}-${j}`} r={r} fonts={fonts} ln={ln} T={c.T} z={stateAt(r, t).print + LEAD * c.T.s} t={t} at={ln.at ?? c.arrive + 0.35 + j * 0.1}
          out={ln.out ?? c.move[0] - 1} shadow={ln.shadow ?? 0} order={2000 + i * 10 + j} about={[...onWall(c.T, [r.W / 2, r.H / 2]), k]} />
      ))))}
    </group>
  );
};

/** How long a line takes to leave, beats: its last word starts first and each one before it a little later. */
const leavingOf = (r: Reel, ln: Line) => (ln.text.split(/\s+/).filter(Boolean).length - 1) * (ln.step ?? r.enter.step) * 0.6 + 0.3;

/** The closer's words, and each post's day beneath its photograph at the depth of its face: another post's as it rises,
 * a moment's as it stands out. When the card's closing page is a shape that sets its own title, the month's line under
 * the wall has left by the time the page comes over it, so only the page's title stands on the end card. */
export const CloserWords: React.FC<{reel: Reel; fonts: Fonts; t: number}> = ({reel: r, fonts, t}) => {
  const c = r.closer;
  const tt = Math.min(t, c.still);
  const out = standOutAt(r, tt);
  const paged = !!closerOf(c.page.name);
  return (
    <group>
      {c.tiles.map((x, j) => (
        <Set key={`d${j}`} r={r} fonts={fonts} ln={x.label} T={WALL_T} z={x.moment ? out + 2 : DAY_DEPTH * Math.min(1.1, risenAt(x, tt)) + 1} t={tt}
          at={x.moment ? c.land : x.at + 0.15} order={2210 + j} />
      ))}
      {c.lines.map((ln, j) => (
        <Set key={`w${j}`} r={r} fonts={fonts} ln={ln} T={WALL_T} z={WORDS_Z} t={tt} at={ln.at ?? (j ? c.sign : c.words)}
          out={paged ? c.page.at - leavingOf(r, ln) : undefined} order={2250 + j} />
      ))}
    </group>
  );
};
