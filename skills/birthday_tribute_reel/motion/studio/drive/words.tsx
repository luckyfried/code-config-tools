// The year's type in the camera's space: each card's name, rising out of its line letter by letter as the card lands,
// its tracking closing as it comes, and lifting off toward the lens as the camera leaves; each card's words rising under
// it word by word; and the cover itself, a sheet of the ground with the age cut through it and its last figure punched
// through on the hit. The wish is the style card's closer's.
import {useMemo} from 'react';
import * as THREE from 'three';
import {clamp01, span} from '../../system/three/motion';
import {Type3D} from '../../system/three/Type3D';
import {fileOf, glyphPath, layout, type Font} from '../../system/three/type';
import {typeZ} from './card';
import {onWall, placeOnWall, type Card, type Line, type Placed, type Plan} from './plan';

const DEPTH = 0.11;
/** Where the closer's cover rests and the wish over it, in world z. */
export const COVER_Z = 120;
/** How far the cover reaches past the frame on every side, in wall px. */
const MARGIN = 260;

/** A line's baseline frame in world space: placed on the wall at depth `z`, tipped back by `tip` about its baseline, its extrusion scaled by `deep`. */
export const frameOf = (plan: Plan, p: Placed, z: number, deep = 1, tip = 0, scale = 1) => {
  const m = new THREE.Matrix4().makeTranslation(p.at[0] - plan.W / 2, plan.H / 2 - p.at[1], z);
  m.multiply(new THREE.Matrix4().makeRotationZ((-p.deg * Math.PI) / 180));
  if (tip) m.multiply(new THREE.Matrix4().makeRotationX(tip));
  m.multiply(new THREE.Matrix4().makeScale(p.size * scale, p.size * scale, p.size * scale * deep));
  return m;
};

type Fonts = Map<string, Font>;
const fontOf = (fonts: Fonts, ln: Line) => fonts.get(fileOf(ln))!;
const colorOf = (plan: Plan, name?: string) => plan.colors[name ?? 'ink'] ?? name ?? plan.colors.ink;
const sideOf = (plan: Plan, name?: string) => (colorOf(plan, name) === plan.colors.accent ? plan.colors.ink : plan.colors.accent);

/** The lens distance of a card's station. */
const lensOf = (plan: Plan, c: Card) => (plan.H * c.T.s) / 2 / Math.tan((30 * Math.PI) / 360);
const SHADOW = 0.42;
/** The flat shadow under a card's type: full under paper-coloured type, light under ink. */
const shadowOf = (c: Card) => (c.type === 'ink' ? 0.14 : SHADOW);

/** A landing's spring: 0 before `at`, a quick swell and a damped settle after. */
const pop = (t: number, at: number, k: number) => (t < at ? 0 : k * Math.sin(Math.min(Math.PI, ((t - at) / 0.35) * Math.PI)) * Math.exp(-(t - at) * 2.5));

/** Beats a name takes to rise out of its line letter by letter, at most and at least (a short card's name rises faster,
 * so it stands at rest for most of its card), and how long before the card lands it starts (the hook's age rises from
 * the film's first frame). */
const ENTER = 1.2;
const QUICK = 0.5;
const EARLY = 0.15;
/** Beats before a card's leave its name lifts off toward the lens. */
const OFF = 0.6;
/** Beats a line of words takes to rise word by word. */
const WORDS = 0.8;

export type Flight = {z: number; tip: number; scale: number; opacity: number; shadow: number; enter: number};

/** When card `c`'s name starts to rise and how many beats it takes. */
const entryOf = (c: Card) => {
  const from = c.hook ? 0 : c.cut - EARLY;
  return {from, len: c.hook ? 0.9 : Math.min(ENTER, Math.max(QUICK, (c.leave - OFF - from) * 0.35))};
};

/** Where a card's name is at beat `t`: rising out of its line letter by letter from just before the card lands,
 * standing with a spring as its last letter lands, and lifting off toward the lens, tipping back and fading, as the camera
 * leaves; it is gone before it grows past the frame's edge or over the next print. null off its card. */
export const headAt = (plan: Plan, c: Card, t: number): Flight | null => {
  const {from, len} = entryOf(c);
  if (t < from || t > c.leave) return null;
  const held = typeZ(c);
  const enter = clamp01((t - from) / len);
  const q = span(t, c.leave - OFF, OFF, (u) => u * u);
  return {z: held + q * lensOf(plan, c) * 0.5, tip: q * 0.5, scale: 1 + pop(t, from + len * 0.7, 0.05), opacity: 1 - span(q, 0.1, 0.35),
    shadow: shadowOf(c) * clamp01(enter * 2) * (1 - q), enter};
};

/** Where the type in flight is at beat `t`, in world space: the name of the card the camera is on; null while none
 * flies. */
export const flightPoint = (plan: Plan, t: number): THREE.Vector3 | null => {
  const at = (p: Placed, z: number) => new THREE.Vector3(p.at[0] - plan.W / 2, plan.H / 2 - p.at[1], z);
  for (const c of plan.cards) {
    const h = headAt(plan, c, t);
    if (h && c.head.length) return at(placeOnWall(c.T, c.head[c.head.length - 1]), h.z);
  }
  return null;
};

/** One card's name, drawn where headAt puts it. */
export const HeadWords: React.FC<{plan: Plan; card: Card; fonts: Fonts; t: number; index: number}> = ({plan, card: c, fonts, t, index}) => {
  const k = headAt(plan, c, t);
  if (!k) return null;
  return (
    <group>
      {c.head.map((ln, i) => (
        <Type3D key={i} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, ln.color)} side={sideOf(plan, ln.color)} anchor={ln.anchor}
          matrix={frameOf(plan, placeOnWall(c.T, ln), k.z, 1, k.tip, k.scale)} depth={DEPTH} enter={k.enter} opacity={k.opacity} shadow={k.shadow} castShadow={k.z > 4}
          renderOrder={2000 + index * 10 + i} />
      ))}
    </group>
  );
};

/** One card's words: rising under its name word by word once its name is half up, gone as the camera leaves. */
export const CardWords: React.FC<{plan: Plan; card: Card; fonts: Fonts; t: number; index: number}> = ({plan, card: c, fonts, t, index}) => {
  const {from, len} = entryOf(c);
  const start = from + len * 0.5;
  if (t < start || t > c.leave) return null;
  const z = typeZ(c);
  const fade = 1 - span(t, c.leave - 0.6, 0.3);
  return (
    <group>
      {c.lines.map((ln, i) => (
        <Type3D key={i} font={fontOf(fonts, ln)} text={ln.text} tracking={ln.tracking} color={colorOf(plan, ln.color)} anchor={ln.anchor}
          matrix={frameOf(plan, placeOnWall(c.T, ln), z)} enter={clamp01((t - (start + i * 0.2)) / WORDS)} by="word" opacity={fade}
          shadow={shadowOf(c)} castShadow renderOrder={1000 + index * 10 + 5} />
      ))}
    </group>
  );
};


/** A glyph run's outlines in wall px (y down), one shape per glyph with its counters as holes. */
const outlinesOf = (font: Font, ln: Line): THREE.Shape[][] => {
  const lay = layout(font, ln.text, ln.tracking ?? 0);
  return lay.glyphs.map((g) => glyphPath(g.glyph, (x, y) => [ln.x + (g.x + x) * ln.size, ln.y + y * ln.size]).toShapes());
};

/**
 * The sheet the giant age is cut out of, in the cover's own frame (x right from the wall's centre, y up from the hinge
 * under the frame's bottom), ending at the wall's edges so a falling sheet shows nothing but the photographs: every figure but the last cut through, and from the punch on the last one too; the counters
 * of the cut figures stay as islands of the sheet.
 */
const coverGeometry = (plan: Plan, glyphs: THREE.Shape[][], open: number) => {
  const {W, H} = plan;
  const local = (p: THREE.Vector2) => new THREE.Vector2(p.x - W / 2, H - p.y + MARGIN);
  const sheet = new THREE.Shape([
    new THREE.Vector2(-W / 2, 0), new THREE.Vector2(W / 2, 0), new THREE.Vector2(W / 2, H + MARGIN), new THREE.Vector2(-W / 2, H + MARGIN),
  ]);
  const islands: THREE.Shape[] = [];
  glyphs.slice(0, open).forEach((shapes) => shapes.forEach((s) => {
    sheet.holes.push(new THREE.Path(s.getPoints(10).map(local)));
    s.holes.forEach((h) => islands.push(new THREE.Shape(h.getPoints(10).map(local))));
  }));
  const geo = new THREE.ShapeGeometry([sheet, ...islands], 10);
  // the cover's picture is the wall itself, so a point of the cover samples the wall it lies over
  const pos = geo.getAttribute('position');
  const uv = geo.getAttribute('uv');
  for (let i = 0; i < pos.count; i++) uv.setXY(i, (pos.getX(i) + W / 2) / W, (pos.getY(i) - MARGIN) / H);
  uv.needsUpdate = true;
  return geo;
};

/** A lit rim along every figure cut through the cover, `width` px wide, in the cover's frame: the cut's edge catching
 * the light so each figure's outline reads at phone size against the photographs around it. */
const rimGeometry = (plan: Plan, glyphs: THREE.Shape[][], open: number, width: number) => {
  const {W, H} = plan;
  const local = (p: THREE.Vector2) => new THREE.Vector2(p.x - W / 2, H - p.y + MARGIN);
  const pos: number[] = [];
  const ribbon = (pts: THREE.Vector2[]) => {
    const n = pts.length;
    for (let i = 0; i < n; i++) {
      const a = pts[i], b = pts[(i + 1) % n];
      const d = b.clone().sub(a);
      if (d.lengthSq() < 1e-6) continue;
      const nrm = new THREE.Vector2(-d.y, d.x).normalize().multiplyScalar(width / 2);
      const q = [a.clone().add(nrm), b.clone().add(nrm), b.clone().sub(nrm), a.clone().sub(nrm)];
      for (const k of [0, 1, 2, 0, 2, 3]) pos.push(q[k].x, q[k].y, 0);
    }
  };
  glyphs.slice(0, open).forEach((shapes) => shapes.forEach((s) => {
    ribbon(s.getPoints(10).map(local));
    s.holes.forEach((h) => ribbon(h.getPoints(10).map(local)));
  }));
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  return geo;
};

/** How the wall is drawn as one picture: `lit`, every photograph at its own exposure edge to edge; `smoked`, a touch
 * soft and its light turned down, the ground a travel crosses before the cards have reached their cells; `sheet`, the
 * photographs sunk deep into the ground's color, the closer's cover, so it reads as a sheet laid over the lit wall and
 * the age cut through it shows the year at full light. */
export type WallMode = 'lit' | 'smoked' | 'sheet';
const DIM: Record<WallMode, {k: number; filter: string; veil: number; op: GlobalCompositeOperation}> = {
  lit: {k: 1, filter: 'none', veil: 0, op: 'source-over'},
  smoked: {k: 0.5, filter: 'blur(1.5px) saturate(0.9) brightness(0.6)', veil: 0.15, op: 'multiply'},
  sheet: {k: 0.5, filter: 'blur(2px) saturate(0.6) brightness(0.45)', veil: 0.6, op: 'source-over'},
};

export const wallOf = (plan: Plan, imageOf: (file: string) => HTMLImageElement | undefined, mode: WallMode) => {
  const {k, filter, veil, op} = DIM[mode];
  const cv = document.createElement('canvas');
  cv.width = Math.round(plan.W * k);
  cv.height = Math.round(plan.H * k);
  const g = cv.getContext('2d')!;
  g.fillStyle = plan.colors.bg;
  g.fillRect(0, 0, cv.width, cv.height);
  g.filter = filter;
  plan.cards.forEach((c) => {
    const img = imageOf(c.file);
    if (!img || !img.width) return;
    const [px, py, pw, ph] = c.place;
    const a = onWall(c.T, [px, py]);
    const b = onWall(c.T, [px + pw, py + ph]);
    g.save();
    g.beginPath();
    c.slot.forEach((p, i) => (i ? g.lineTo(p[0] * k, p[1] * k) : g.moveTo(p[0] * k, p[1] * k)));
    g.closePath();
    g.clip();
    g.drawImage(img, a[0] * k, a[1] * k, (b[0] - a[0]) * k, (b[1] - a[1]) * k);
    g.restore();
  });
  g.filter = 'none';
  if (veil) {
    g.globalCompositeOperation = op;
    g.fillStyle = plan.colors.bg;
    g.globalAlpha = veil;
    g.fillRect(0, 0, cv.width, cv.height);
  }
  const out = new THREE.CanvasTexture(cv);
  out.colorSpace = THREE.SRGBColorSpace;
  return out;
};

/** The closer's cover, a sheet of the ground carrying the wall's photographs sunk into it: standing up off the wall's bottom
 * edge as the camera reaches the wall, falling shut on the riser and slamming down on the impact with the year showing
 * clear through the age, and its last figure punched through on the hit, its lit rim slamming in from a little larger
 * and settling past its size. The age is one form throughout: figures cut through the sheet. */
export const Cover: React.FC<{plan: Plan; fonts: Fonts; t: number; imageOf: (file: string) => HTMLImageElement | undefined}> = ({plan, fonts, t, imageOf}) => {
  const big = plan.closer.big;
  const font = fontOf(fonts, big);
  const C = plan.closer.at;
  const glyphs = useMemo(() => (font ? outlinesOf(font, big) : []), [font, big]);
  const before = useMemo(() => coverGeometry(plan, glyphs, glyphs.length - 1), [plan, glyphs]);
  const after = useMemo(() => coverGeometry(plan, glyphs, glyphs.length), [plan, glyphs]);
  const rim = useMemo(() => rimGeometry(plan, glyphs, glyphs.length - 1, 12), [plan, glyphs]);
  // the last figure's rim alone, centred on its own middle so it can slam in about it
  const punched = useMemo(() => {
    const geo = rimGeometry(plan, glyphs.slice(-1), 1, 12);
    geo.computeBoundingBox();
    const mid = geo.boundingBox!.getCenter(new THREE.Vector3());
    geo.translate(-mid.x, -mid.y, 0);
    return {geo, mid};
  }, [plan, glyphs]);
  const mats = useMemo(() => ({
    sheet: new THREE.MeshBasicMaterial({map: wallOf(plan, imageOf, 'sheet'), toneMapped: false, side: THREE.DoubleSide}),
    shade: new THREE.ShadowMaterial({opacity: 0.28, transparent: true, depthWrite: false}),
    rim: new THREE.MeshBasicMaterial({color: plan.colors.paper, toneMapped: false, side: THREE.DoubleSide}),
  }), [plan, imageOf]);
  if (t < C + 0.4) return null;
  const q = clamp01((t - (C + 0.45)) / 0.8);
  const bounce = t > C + 1.25 ? 0.03 * Math.max(0, Math.sin(Math.PI * clamp01((t - C - 1.25) / 0.22))) : 0;
  const angle = (Math.PI / 2 - 0.04) * (1 - q * q) + bounce;
  const punch = t >= C + 3.0;
  const geo = punch ? after : before;
  const u = clamp01((t - (C + 3.0)) / 0.3);
  const size = 1 + 0.3 * (1 - (1 + 2.4 * (u - 1) ** 3 + 1.4 * (u - 1) ** 2));
  return (
    <group position={[0, -plan.H / 2 - MARGIN, COVER_Z]} rotation={[angle, 0, 0]}>
      <mesh geometry={geo} material={mats.sheet} castShadow renderOrder={1500} />
      <mesh geometry={geo} material={mats.shade} position={[0, 0, 0.05]} receiveShadow renderOrder={1501} />
      <mesh geometry={rim} material={mats.rim} position={[0, 0, 0.1]} renderOrder={1502} />
      {punch ? <mesh geometry={punched.geo} material={mats.rim} position={[punched.mid.x, punched.mid.y, 0.1]} scale={[size, size, 1]} renderOrder={1502} /> : null}
    </group>
  );
};
