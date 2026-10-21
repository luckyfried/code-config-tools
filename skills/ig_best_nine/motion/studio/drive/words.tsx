// The drive film's type in the camera's space: the hook's total rolling up and breaking into the nine counts, each
// count landing on its edge rolling up from the one before and moving into its place on the closer's wall, the rank
// and caption rising beside it, and the closer's own lines.
import * as THREE from 'three';
import {bezier, lerp, mixPt, span} from '../../system/three/motion';
import {Type3D, type Roll} from '../../system/three/Type3D';
import {fileOf, type Font} from '../../system/three/type';
import {liftOf} from './card';
import {placeOnWall, type Card, type Line, type Placed, type Plan, type Xf} from './plan';

const WALL: Xf = {s: 1, o: [0, 0]};
const DEPTH = 0.11;

/** A line's baseline frame in world space: placed on the wall at depth `z`, tipped back by `tip` about its baseline, its extrusion scaled by `deep`. */
export const frameOf = (plan: Plan, p: Placed, z: number, deep = 1, tip = 0, scale = 1) => {
  const m = new THREE.Matrix4().makeTranslation(p.at[0] - plan.W / 2, plan.H / 2 - p.at[1], z);
  m.multiply(new THREE.Matrix4().makeRotationZ((-p.deg * Math.PI) / 180));
  if (tip) m.multiply(new THREE.Matrix4().makeRotationX(tip));
  m.multiply(new THREE.Matrix4().makeScale(p.size * scale, p.size * scale, p.size * scale * deep));
  return m;
};

const mixPlaced = (a: Placed, b: Placed, u: number): Placed => ({at: mixPt(a.at, b.at, u), deg: lerp(a.deg, b.deg, u), size: a.size * Math.pow(b.size / a.size, u)});

type Fonts = Map<string, Font>;
const fontOf = (fonts: Fonts, ln: Line) => fonts.get(fileOf(ln))!;
const colorOf = (plan: Plan, name?: string) => plan.colors[name ?? 'ink'] ?? name ?? plan.colors.ink;
const sideOf = (plan: Plan, name?: string) => (colorOf(plan, name) === plan.colors.accent ? plan.colors.ink : plan.colors.accent);

/** A roll from `a` to `b` over [t0, t0 + len] beats, at each instant the shutter saw ending at `t`. */
const rollSamples = (plan: Plan, t: number, t0: number, len: number, a: number, b: number): Roll => {
  const half = 0.5 / plan.pulse;
  const p = [4, 3, 2, 1, 0].map((k) => Math.min(1, Math.max(0, (t - (half * k) / 4 - t0) / len)));
  return {from: a, to: b, p: p[4] - p[0] < 0.002 ? [p[4]] : p};
};

/** One card's count and words. */
export const CardWords: React.FC<{plan: Plan; card: Card; fonts: Fonts; t: number; index: number}> = ({plan, card: c, fonts, t, index}) => {
  if (!c.count || t < c.cut) return null;
  const enter = bezier(plan.ease.enter);
  const move = bezier(plan.ease.move);
  const s = c.T.s;
  const lift = liftOf(c);
  const D = (plan.H * s) / 2 / Math.tan((30 * Math.PI) / 360);
  const land = span(t, c.cut, 0.5, bezier([0.15, 0.85, 0.3, 1]));
  const pop = enter(Math.min(1, (t - c.cut) / 0.55));
  const leave = span(t, c.leave - 0.6, 0.75, move);
  const edge = placeOnWall(c.T, c.count);
  const slot = c.slotCount ? placeOnWall(WALL, c.slotCount) : edge;
  const p = mixPlaced(edge, slot, c.slotCount ? leave : 0);
  const z = lerp(lift + 7 * s, 0.6, leave) + (1 - land) * D * 0.55;
  const order = 1000 + index * 10;
  const lines = c.rest.map((ln, i) => {
    const carried = c.slotRest[ln.name ?? ''];
    const from = placeOnWall(c.T, ln);
    const pl = carried ? mixPlaced(from, placeOnWall(WALL, carried), leave) : from;
    const rise = enter(Math.min(1, Math.max(0, (t - (c.cut + 0.35 + i * 0.08)) / 0.4)));
    const fade = carried ? 1 : 1 - span(t, c.leave - 0.6, 0.3);
    return (
      <Type3D key={i} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, (carried ?? ln).color)} anchor={ln.anchor}
        matrix={frameOf(plan, pl, lerp(lift + 7 * s, 1.0, leave))} rise={Math.min(1, rise)} opacity={fade} renderOrder={order + 5} />
    );
  });
  return (
    <group>
      <Type3D font={fontOf(fonts, c.count)} text={c.count.text} tracking={c.count.tracking} color={colorOf(plan, c.count.color)} side={sideOf(plan, c.count.color)}
        matrix={frameOf(plan, p, z, lerp(1, 0.35, leave), (1 - land) * -1.25, Math.max(0.2, pop))} depth={DEPTH}
        roll={c.count.count ? rollSamples(plan, t, c.cut, c.count.count[2], c.count.count[0], c.count.count[1]) : undefined} opacity={c.slotCount ? 1 : 1 - leave} shadow={0.16 * land * (1 - leave)}
        castShadow={z > 4} renderOrder={order} />
      {lines}
    </group>
  );
};

/** The hook's words: the handle and its line rising, the total landing and rolling up, then breaking into the counts that fly at the lens. */
export const HookWords: React.FC<{plan: Plan; fonts: Fonts; t: number}> = ({plan, fonts, t}) => {
  const hook = plan.cards[0];
  const total = plan.total;
  if (!total) return null;
  const enter = bezier(plan.ease.enter);
  const s = hook.T.s;
  const lift = liftOf(hook);
  const D = (plan.H * s) / 2 / Math.tan((30 * Math.PI) / 360);
  // the total rolls from the blade opening the photograph and lands on the beat its count names
  const [t0, , beats] = total.count ?? [0, 0, 2];
  const start = 0.3;
  const land = span(t, start, 0.5, bezier([0.15, 0.85, 0.3, 1]));
  const B = plan.breakAt;
  const gone = span(t, B, 0.12);
  const pl = placeOnWall(hook.T, total);
  const font = fontOf(fonts, total);
  const kick = plan.kicker.map((ln, i) => {
    const rise = enter(Math.min(1, Math.max(0, (t - (start + 0.05 + i * 0.15)) / 0.45)));
    return (
      <Type3D key={i} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, ln.color)} matrix={frameOf(plan, placeOnWall(hook.T, ln), lift + 8 * s)}
        rise={Math.min(1, rise)} opacity={1 - span(t, B - 0.05, 0.3)} renderOrder={1005} />
    );
  });
  // the total's figure along its baseline, for where each count breaks out of it
  const advance = (text: string) => (font ? font.stringToGlyphs(text).reduce((w: number, g: any) => w + g.advanceWidth, 0) / font.unitsPerEm : 0);
  const width = advance(total.text) * pl.size;
  const a = (pl.deg * Math.PI) / 180;
  const dir: [number, number] = [Math.cos(a), Math.sin(a)];
  const n = plan.shards.length;
  // the middle of the figure, where the counts gather into the best-nine grid, rank 1 at its top left
  const cx = pl.at[0] + (dir[0] * width) / 2 + Math.sin(a) * pl.size * 0.35;
  const cy = pl.at[1] + (dir[1] * width) / 2 - Math.cos(a) * pl.size * 0.35;
  const shards = t < B ? null : plan.shards.map((sh, i) => {
    // each count breaks out of the figure into its cell of a three by three grid, where the nine hang readable for most
    // of a beat before the grid bursts at the lens
    const out = enter(Math.min(1, Math.max(0, (t - B - i * 0.02) / 0.4)));
    const fly = span(t, B + 0.8 + i * 0.02, 0.45, bezier([0.5, 0, 0.9, 0.6]));
    if (fly >= 1) return null;
    const u = (i + 0.5) / n;
    const size = pl.size * 0.3 * (0.5 + 0.5 * sh.size);
    const col = (sh.rank - 1) % 3, row = Math.floor((sh.rank - 1) / 3);
    const cell: [number, number] = [cx + (col - 1) * 300 * s - (advance(String(sh.value)) * size) / 2, cy - (2 - row) * 0.42 * pl.size + size * 0.35];
    const from: [number, number] = [pl.at[0] + dir[0] * width * u, pl.at[1] + dir[1] * width * u - pl.size * 0.35];
    const ang = Math.atan2(cell[1] - cy, cell[0] - cx) + (i % 2 ? 0.3 : -0.3);
    const away: [number, number] = [Math.cos(ang) * 570 * s * fly, Math.sin(ang) * 480 * s * fly];
    const at: [number, number] = [lerp(from[0], cell[0], out) + away[0], lerp(from[1], cell[1], out) + away[1]];
    const p: Placed = {at, deg: pl.deg * (1 - out) + (i % 2 ? 9 : -9) * (1 - out) * Math.min(1, out * 4) + fly * (i % 2 ? 40 : -40), size};
    const ln: Line = {...total, text: String(sh.value)};
    return (
      <Type3D key={sh.rank} font={font} text={ln.text} tracking={total.tracking} color={colorOf(plan, total.color)} side={sideOf(plan, total.color)}
        matrix={frameOf(plan, p, lift + 20 * s + fly * fly * D * 0.92, 1, 0, Math.max(0.05, out))} depth={DEPTH} castShadow renderOrder={1100 + i} />
    );
  });
  return (
    <group>
      {kick}
      {gone < 1 ? (
        <Type3D font={font} text={total.text} tracking={total.tracking} color={colorOf(plan, total.color)} side={sideOf(plan, total.color)}
          matrix={frameOf(plan, pl, lift + 8 * s + (1 - land) * D * 0.5, 1, (1 - land) * -1.2, (1 + 0.08 * gone) * Math.max(0.2, enter(Math.min(1, (t - start) / 0.55))))}
          depth={DEPTH} roll={rollSamples(plan, t, start, beats - start, t0, total.count?.[1] ?? 0)} opacity={1 - gone}
          shadow={0.16 * land} castShadow renderOrder={1000} />
      ) : null}
      {shards}
    </group>
  );
};

/** A line's full stop on the closer's wall: on its baseline just past its last letter, in world space, with the radius
 * of a full stop at the line's size. */
const stopAfter = (plan: Plan, fonts: Fonts, ln: Line) => {
  const p = placeOnWall(WALL, ln);
  const font = fontOf(fonts, ln);
  const width = font ? (font.stringToGlyphs(ln.text).reduce((w: number, g: any) => w + g.advanceWidth, 0) / font.unitsPerEm) * p.size : 0;
  const r = Math.max(9, 0.09 * p.size);
  const a = (p.deg * Math.PI) / 180;
  const along = width + 0.06 * p.size + r;
  const x = p.at[0] + Math.cos(a) * along + Math.sin(a) * r;
  const y = p.at[1] + Math.sin(a) * along - Math.cos(a) * r;
  return {p: new THREE.Vector3(x - plan.W / 2, plan.H / 2 - y, 2.5), r};
};

/** Where the dot lands on the closer's wall, in the countdown's order: the full stop after each count below the top
 * post's, then the full stop after the ask, the closer's last line. */
export const routeOf = (plan: Plan, fonts: Fonts): {p: THREE.Vector3; r: number}[] => {
  const counts = plan.cards.filter((c) => !c.hook && c.slotCount).slice(0, -1).map((c) => stopAfter(plan, fonts, c.slotCount!));
  const ask = plan.closer.lines.at(-1);
  return [...counts, ...(ask ? [stopAfter(plan, fonts, ask)] : [])];
};

/** The closer's own lines (the handle and the ask), rising onto the wall as the dot reaches the top count, settled by the still. */
export const CloserWords: React.FC<{plan: Plan; fonts: Fonts; t: number}> = ({plan, fonts, t}) => {
  const enter = bezier(plan.ease.enter);
  const n = plan.closer.lines.length;
  const C = plan.closer.still - 0.6 - 0.1 * (n - 1);
  if (t < C) return null;
  return (
    <group>
      {plan.closer.lines.map((ln, i) => (
        <Type3D key={i} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, ln.color)} anchor={ln.anchor}
          matrix={frameOf(plan, placeOnWall(WALL, ln), 1.2)} rise={Math.min(1, enter(Math.min(1, Math.max(0, (t - C - i * 0.1) / 0.45))))} renderOrder={1500} />
      ))}
    </group>
  );
};
