// The linen crop frame the film carries from the hook to the closer: four bars round a box, eased from key to key,
// landing a touch past its place and settling, lighting up as it lands or locks; and its band, hinged on the frame's
// top edge (or on a side bar, its top at the frame's top), unrolling out of the hinge, tipped toward the lens as it
// starts and lying flat as it overshoots and settles, to show its words: the film's hook and each held post's caption,
// in the display face extruded, and the closer's handle, bio and ask. The band's paper glows a little of its own
// color so it is paper from every angle. Words enter letter by letter or word by word, each rising out of its
// baseline on the kit's enter curve, tracked out and closing up as it lands, unrolled with the band while it opens,
// and sink back under their baselines on the exit curve as the band starts to roll back into the hinge.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span} from '../../system/three/motion';
import {Type3D} from '../../system/three/Type3D';
import {fileOf, type Font} from '../../system/three/type';
import {toWorld, type Band, type BandSide, type Box, type FrameKey, type Line, type Plan} from './plan';

export const BAND_W = 620;
const FT = 16;
const DEPTH = 9;

// the frame's curves, each the card's: `move` and `close` its move curve, `land` and `spring` its entrance (which
// overshoots and settles on a card whose entrance does), `fall` its exit, accelerating into the landing like a thing
// let go, and `drop` its move curve drawing back first by half as much as its entrance overshoots (the anticipation of
// the drop into the grid, none on a card whose entrance never overshoots); post.tsx moves the photograph on the same
// curves
export const easeOf = (plan: Plan): Record<FrameKey['ease'], number[]> => {
  const {enter, exit, move} = plan.ease;
  const back = Math.max(0, enter[1] - 1, enter[3] - 1) * 0.5;
  return {move, close: move, land: enter, spring: enter, fall: exit, drop: [move[0], -back, move[2], 1]};
};
const FLASH: Partial<Record<FrameKey['ease'], number>> = {land: 0.6, spring: 0.6, fall: 0.8, close: 1};
// how far a move between two places lifts off the wall toward the lens, per px it travels; post.tsx lifts the
// photograph it carries by the same share
export const ARC = 0.06;
const RISE = 0.45;
const SINK = 0.3;
// how far the band tips toward the lens while it starts to unroll, radians
const TIP = 0.5;

/** The frame's box and depth at beat `t`; a move between two places arcs off the wall by ARC of its length. */
export const frameAt = (plan: Plan, t: number): {box: Box; z: number; flash: number} => {
  const keys = plan.frame;
  let flash = 0;
  for (const k of keys) if (FLASH[k.ease] && t >= k.t) flash = Math.max(flash, Math.exp(-(t - k.t) * 5) * FLASH[k.ease]!);
  if (t <= keys[0].t) return {box: keys[0].box, z: keys[0].z, flash};
  for (let i = 0; i + 1 < keys.length; i++) {
    const a = keys[i], b = keys[i + 1];
    if (t > b.t) continue;
    const u = bezier(easeOf(plan)[b.ease])(clamp01((t - a.t) / Math.max(1e-6, b.t - a.t)));
    const box = a.box.map((v, j) => lerp(v, b.box[j], u)) as Box;
    const dist = Math.hypot(b.box[0] - a.box[0] + (b.box[2] - a.box[2]) / 2, b.box[1] - a.box[1] + (b.box[3] - a.box[3]) / 2);
    return {box, z: lerp(a.z, b.z, u) + Math.sin(Math.PI * clamp01(u)) * ARC * dist, flash};
  }
  const k = keys[keys.length - 1];
  return {box: k.box, z: k.z, flash};
};

// the band unrolls on the card's entrance (running a touch past open and settling where that overshoots) and rolls
// back in on its exit

/** The band's opening (0 rolled into its hinge, 1 open, a touch past 1 as it overshoots), the words it carries and its side at beat `t`. */
export const bandAt = (plan: Plan, t: number) => {
  const keys = plan.bandKeys;
  let i = 0;
  while (i + 1 < keys.length && keys[i + 1].t <= t) i++;
  const a = keys[i], b = keys[i + 1] ?? a;
  const u = b === a ? 1 : bezier(b.open > a.open ? plan.ease.enter : plan.ease.exit)(clamp01((t - a.t) / Math.max(1e-6, b.t - a.t)));
  return {open: t < a.t ? a.open : lerp(a.open, b.open, u), band: a.band, side: (a.side ?? 'top') as BandSide};
};

/** The band's hinge in world space and its own px (bx, by from its top left) in the hinge's axes, for a frame at `box`
 * and depth `z`: hinged on the top bar's top edge, or on a side bar's outer edge; its own px run from its top left,
 * band.w wide (BAND_W when unset) at s = 1, centered on the frame above it. */
const hingeOf = (plan: Plan, box: Box, z: number, side: BandSide, band: Band) => {
  const s = box[2] / BAND_W;
  const ft = FT * s;
  const [x, y, w] = box;
  const bw = band.w ?? BAND_W;
  const dx = side === 'top' ? (BAND_W - bw) / 2 : 0;
  const hingeAt: Record<BandSide, [number, number]> = {top: [x, y - ft], right: [x + w + ft, y - ft], left: [x - ft, y - ft]};
  const hinge = new THREE.Vector3(...toWorld(plan, hingeAt[side], z + DEPTH * s));
  const local = (bx: number, by: number): [number, number] =>
    side === 'top' ? [(bx + dx) * s, (band.h - by) * s] : side === 'right' ? [(bx + FT) * s, -by * s] : [(bx - BAND_W - FT) * s, -by * s];
  return {hinge, local, bw};
};

type Fonts = Map<string, Font>;

export const FrameView: React.FC<{plan: Plan; t: number; fonts: Fonts}> = ({plan, t, fonts}) => {
  // the bars draw over every photograph, so a picture that comes in from the lens never hides the frame it is carried by
  const mats = useMemo(() => ({
    bar: new THREE.MeshStandardMaterial({color: plan.colors.paper, roughness: 0.82, metalness: 0, emissive: new THREE.Color(plan.colors.paper),
      transparent: true, depthTest: false}),
    band: new THREE.MeshStandardMaterial({color: plan.colors.paper, roughness: 0.9, metalness: 0, emissive: new THREE.Color(plan.colors.paper),
      emissiveIntensity: 0.22}),
  }), [plan]);
  const geo = useMemo(() => new THREE.BoxGeometry(1, 1, 1), []);
  const {box, z, flash} = frameAt(plan, t);
  const {open, band: bandId, side} = bandAt(plan, t);
  const band = plan.bands[bandId];
  const s = box[2] / BAND_W;
  const ft = FT * s;
  const dz = DEPTH * s;
  mats.bar.emissiveIntensity = 0.15 + 1.6 * flash;
  const [x, y, w, h] = box;
  const bars: [number, number, number, number][] = [
    [x - ft, y - ft, w + 2 * ft, ft], [x - ft, y + h, w + 2 * ft, ft], [x - ft, y, ft, h], [x + w, y, ft, h],
  ];
  const meshes = bars.map(([bx, by, bw, bh], i) => {
    const c = toWorld(plan, [bx + bw / 2, by + bh / 2], z + dz / 2);
    return (
      <mesh key={i} geometry={geo} material={mats.bar} position={c} scale={[bw, bh, dz]} castShadow={z > 6} renderOrder={900} />
    );
  });
  const {hinge, local, bw} = hingeOf(plan, box, z, side, band);
  const hb = band.h * s;
  // the band unrolls out of its hinge: it grows from the hinge to its full height (its width beside the frame), tipped
  // toward the lens by up to TIP while it is short, and the words unroll with it
  const g = Math.max(0, open);
  const angle = (1 - clamp01(open)) * TIP;
  const turn = side === 'top' ? new THREE.Matrix4().makeRotationX(angle) : new THREE.Matrix4().makeRotationY(side === 'right' ? -angle : angle);
  const unroll = (k: number) => (side === 'top' ? new THREE.Matrix4().makeScale(1, k, 1) : new THREE.Matrix4().makeScale(k, 1, 1));
  const frameM = new THREE.Matrix4().makeTranslation(hinge.x, hinge.y, hinge.z).multiply(turn).multiply(unroll(Math.min(1, g)));
  const paperM = new THREE.Matrix4().makeTranslation(hinge.x, hinge.y, hinge.z).multiply(turn).multiply(unroll(g));
  const bandM = (bx: number, by: number, dzz: number) => frameM.clone().multiply(new THREE.Matrix4().makeTranslation(...local(bx, by), dzz));
  const showBand = open > 0.01;
  const bandMesh = showBand ? (() => {
    const m = paperM.clone().multiply(new THREE.Matrix4().makeTranslation(...local(bw / 2, band.h / 2), -dz / 2 + 2.5 * s))
      .multiply(new THREE.Matrix4().makeScale(bw * s + 2 * ft, hb, 5 * s));
    const p = new THREE.Vector3(), q = new THREE.Quaternion(), sc = new THREE.Vector3();
    m.decompose(p, q, sc);
    return <mesh geometry={geo} material={mats.band} position={p} quaternion={q} scale={sc} castShadow renderOrder={901} />;
  })() : null;
  const enter = bezier(plan.ease.enter);
  const exit = bezier(plan.ease.exit);
  const sunk = band.sink === undefined ? 1 : 1 - exit(clamp01((t - band.sink) / SINK));
  const words = showBand && sunk > 0 ? band.lines.map((ln: Line, i) => {
    const font = fonts.get(fileOf({face: ln.face, weight: ln.weight}));
    if (!font) return null;
    const riseAt = band.rise?.[ln.name];
    const at = (k: number) => (riseAt === undefined ? 1 : enter(clamp01((t - riseAt - k * (ln.stagger ?? 0)) / RISE)) * sunk);
    const rise = at(0);
    if (rise <= 0) return null;
    const riseOf = ln.by === 'letter' ? (g: number) => at(g) : ln.by === 'word' ? (_: number, w: number) => at(w) : undefined;
    // the band's face is 0.5 s off the hinge; the words stand a whole unit clear of it, so depth never fights at a far camera
    const m = bandM(ln.x, ln.y, 1.5 * s).multiply(new THREE.Matrix4().makeScale(ln.size * s, ln.size * s, ln.size * s));
    const display = ln.face === 'display';
    return (
      <Type3D key={`${bandId}-${i}`} font={font} text={ln.text} tracking={ln.tracking} color={plan.colors[ln.color] ?? plan.colors.ink}
        side={display ? plan.colors.bg : undefined} matrix={m} depth={display ? 0.1 : 0} rise={rise} riseOf={riseOf} track={ln.track ?? 0}
        renderOrder={950 + i} />
    );
  }) : null;
  return (
    <group>
      {meshes}
      {bandMesh}
      {words}
    </group>
  );
};
