// The tag: the one thing that travels the whole film. On the hook a tag pops onto every head in the photograph of
// them together, then the tags shrink to dots and gather into one. That dot leaves with the camera, arcs to the next
// person and opens into their tag, pointing at them, with their handle; when the camera leaves, the tag shrinks back
// to the dot and flies on. On the closer it runs the wall in the film's order, leaving a tag on every face, and
// the tag it opens on the last is the film's last move.
import {useEffect, useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span, type Pt} from '../../system/three/motion';
import {Type3D} from '../../system/three/Type3D';
import {liftOf, typeZ} from './card';
import {onWall, WALL, type Card, type Plan, type Tag, type Xf} from './plan';
import {colorOf, fontOf, frameOf, type Fonts} from './words';

/** A tag's dot, as a share of the tag's height. */
const DOT = 0.5;
const TRAIL = 10;
/** Beats a tag takes to open from its dot, and to close back into it. */
const OPEN = 0.22;
const CLOSE = 0.15;

/** A tag in world space: its tip, its pill (left, top, right, bottom; y up), its type size, its depth, and the x its
 * text starts at in the open pill. */
export type Pill = {tag: Tag; tip: THREE.Vector3; box: [number, number, number, number]; size: number; z: number; tx: number};

export const pillOf = (plan: Plan, T: Xf, tag: Tag, z: number): Pill => {
  const w = (p: Pt) => onWall(T, p);
  const a = w([tag.box[0], tag.box[1]]), b = w([tag.box[2], tag.box[3]]), tip = w(tag.tip);
  return {
    tag, z, size: tag.size * T.s,
    tip: new THREE.Vector3(tip[0] - plan.W / 2, plan.H / 2 - tip[1], z),
    box: [a[0] - plan.W / 2, plan.H / 2 - a[1], b[0] - plan.W / 2, plan.H / 2 - b[1]],
    tx: tag.inset !== undefined ? onWall(T, [tag.inset, 0])[0] - plan.W / 2 : a[0] - plan.W / 2 + 0.62 * tag.size * T.s,
  };
};

const dotOf = (p: Pill) => DOT * (p.box[1] - p.box[3]);
/** A tag's depth: on a photograph, just behind the type and in front of the part the blade lifts and tips toward the
 * lens, so a tag above the edge stays on top of it. */
const pillZ = (c: Card) => (c.field === 'photo' ? typeZ(c) - 4 * c.T.s : liftOf(c) + 14 * c.T.s);

/** The rounding of a tag's corners in its shape, as a share of its height: none on a band or a block. */
const ROUND: Record<string, number> = {pill: 0.28, band: 0, block: 0, sticker: 0.3, stamp: 0.12};

/** The rounded box `w` by `h` centred on the origin, corners `r`. */
const roundBox = (w: number, h: number, r: number) => {
  const s = new THREE.Shape();
  const L = -w / 2, R = w / 2, B = -h / 2, T = h / 2;
  s.moveTo(L + r, B);
  s.lineTo(R - r, B);
  if (r > 0) s.absarc(R - r, B + r, r, -Math.PI / 2, 0, false);
  s.lineTo(R, T - r);
  if (r > 0) s.absarc(R - r, T - r, r, 0, Math.PI / 2, false);
  s.lineTo(L + r, T);
  if (r > 0) s.absarc(L + r, T - r, r, Math.PI / 2, Math.PI, false);
  s.lineTo(L, B + r);
  if (r > 0) s.absarc(L + r, B + r, r, Math.PI, Math.PI * 1.5, false);
  return s;
};

/** The pill's outline at `u` (0 a dot on the tip, 1 the whole tag), centred on its own origin, and where that origin is;
 * `grow` px wider on every side (a sticker's white edge). A stamp is a thin frame round its text; a tag in a look's own
 * shape has no pointer. */
const outline = (p: Pill, u: number, grow = 0, solid = false) => {
  const [x0, y1, x1, y0] = p.box;
  const H = y1 - y0, W = x1 - x0;
  const d = dotOf(p);
  const shape = p.tag.shape ?? 'pill';
  const w = lerp(d, W, u) + 2 * grow * u, h = lerp(d, H, u) + 2 * grow * u;
  const r = Math.min(h / 2, lerp(d / 2, ROUND[shape] * H + grow, u));
  const cx = lerp(p.tip.x, (x0 + x1) / 2, u), cy = lerp(p.tip.y, (y0 + y1) / 2, u);
  if (shape !== 'pill') {
    const s = roundBox(w, h, r);
    if (shape === 'stamp' && u > 0.3 && !solid) {
      const k = 0.09 * p.size * u;
      s.holes.push(roundBox(w - 2 * k, h - 2 * k, Math.max(0, r - k)));
    }
    return {shapes: [s], c: new THREE.Vector3(cx, cy, p.z)};
  }
  const s = roundBox(w, h, r);
  const L = -w / 2, R = w / 2, B = -h / 2, T = h / 2;
  const shapes = [s];
  if (u > 0.02) {
    // the pointer: its point on the tip, its base on the pill's near edge
    const below = p.tag.side === 'below';
    const edge = below ? T : B;
    const ax = Math.max(L + r + 0.42 * p.size * u, Math.min(R - r - 0.42 * p.size * u, p.tip.x - cx));
    const half = 0.42 * p.size * u;
    const tri = new THREE.Shape();
    const apex = edge + (below ? 1 : -1) * Math.abs(p.tip.y - (cy + edge)) * u;
    tri.moveTo(ax - half, edge);
    tri.lineTo(ax + half, edge);
    tri.lineTo(lerp(ax, p.tip.x - cx, u), apex);
    tri.closePath();
    shapes.push(tri);
  }
  return {shapes, c: new THREE.Vector3(cx, cy, p.z)};
};

/** One tag at `u` (0 its dot, 1 open), its handle growing with it: the handle rises into the pill as it opens from its
 * dot and stays in it, at the pill's own scale, as it closes back into the dot, so no tag is ever an empty pill. A
 * sticker lies on its white edge and a stamp on near black; a tag turned in its shape turns about its middle, its text with it; a marquee's text
 * runs `shift` px left, followed by itself. */
const PillView: React.FC<{plan: Plan; pill: Pill; u: number; opacity?: number; fonts: Fonts; order: number; shift?: number}> = ({plan, pill, u, opacity = 1, fonts, order, shift = 0}) => {
  const k = Math.round(u * 400) / 400;
  const shape = pill.tag.shape ?? 'pill';
  const {shapes, c} = useMemo(() => outline(pill, k), [pill, k]);
  // a sticker lies on its white edge; a stamp's frame is filled with near black, so its text reads over any picture
  const edged = useMemo(() => (shape === 'sticker' ? outline(pill, k, 0.16 * pill.size).shapes : shape === 'stamp' ? outline(pill, k, 0, true).shapes : null), [pill, k, shape]);
  const geo = useMemo(() => new THREE.ShapeGeometry(shapes, 10), [shapes]);
  const edgeGeo = useMemo(() => (edged ? new THREE.ShapeGeometry(edged, 10) : null), [edged]);
  useEffect(() => () => geo.dispose(), [geo]);
  useEffect(() => () => edgeGeo?.dispose(), [edgeGeo]);
  const mat = useMemo(() => new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false}), []);
  const edgeMat = useMemo(() => new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false, side: THREE.DoubleSide}), []);
  const ink = pill.tag.ink ? colorOf(plan, pill.tag.ink) : null;
  mat.color.set(ink ?? plan.colors.accent);
  mat.opacity = opacity;
  edgeMat.color.set(shape === 'stamp' ? '#140d08' : '#ffffff');
  edgeMat.opacity = opacity;
  if (opacity <= 0.002) return null;
  const text = span(u, 0.04, 0.16);
  const [x0, , x1] = pill.box;
  // the handle's start in the open pill, carried in toward the pill's middle and scaled with it as it opens and closes
  const ox = pill.tx - (x0 + x1) / 2 - shift, oy = -0.36 * pill.size;
  const grow = Math.max(0, u);
  const at: Pt = [c.x + ox * grow + plan.W / 2, plan.H / 2 - (c.y + oy * grow)];
  const turn = (-(pill.tag.turn ?? 0) * Math.PI) / 180;
  const about = new THREE.Matrix4().makeTranslation(c.x, c.y, 0).multiply(new THREE.Matrix4().makeRotationZ(turn))
    .multiply(new THREE.Matrix4().makeTranslation(-c.x, -c.y, 0));
  const words = pill.tag.scroll ? `${pill.tag.text}  ·  ${pill.tag.text}  ·  ${pill.tag.text}` : pill.tag.text;
  return (
    <group>
      {edgeGeo ? <mesh geometry={edgeGeo} material={edgeMat} position={[c.x, c.y, c.z - 0.1]} rotation={[0, 0, turn]} renderOrder={order} /> : null}
      <mesh geometry={geo} material={mat} position={c} rotation={[0, 0, turn]} renderOrder={order} />
      {text > 0.002 ? (
        <Type3D font={fontOf(fonts, pill.tag)} text={words} color={ink ?? plan.tagText}
          matrix={about.clone().multiply(frameOf(plan, {at, deg: 0, size: pill.size * grow}, pill.z + 0.3))}
          rise={text} opacity={opacity} renderOrder={order + 1} />
      ) : null}
    </group>
  );
};

/** A tag opening on the beat it lands: it overshoots a touch and settles. */
const opening = (t: number, at: number) => {
  const x = clamp01((t - at) / OPEN);
  return 1 + 2.2 * Math.pow(x - 1, 3) + 1.2 * Math.pow(x - 1, 2);
};

type Leg = {a: THREE.Vector3; b: THREE.Vector3; da: number; db: number; go: number; land: number; s: number};

/** The film's tags and their schedule: the hook's tags, each person's tag on their card, their tags on the wall, and
 * the legs the dot flies between them. */
export const tagsOf = (plan: Plan) => {
  const [hook, ...people] = plan.cards;
  const hookPills = hook.tags.map((tg) => pillOf(plan, hook.T, tg, pillZ(hook)));
  const cardPills = people.map((c) => (c.tags[0] ? pillOf(plan, c.T, c.tags[0], pillZ(c)) : null));
  const wallPills = people.map((c) => (c.wallTag ? pillOf(plan, WALL, c.wallTag, 2.5) : null));
  const G = hookPills.length
    ? hookPills.reduce((v, p) => v.add(p.tip), new THREE.Vector3()).multiplyScalar(1 / hookPills.length).setZ(pillZ(hook))
    : new THREE.Vector3(0, 0, pillZ(hook));
  const gDot = hookPills.length ? dotOf(hookPills[0]) * 1.3 : 20 * hook.T.s;
  const legs: Leg[] = [];
  let at = {p: G, d: gDot, t: hook.go, s: hook.T.s};
  people.forEach((c, i) => {
    const pl = cardPills[i];
    if (!pl) return;
    legs.push({a: at.p, b: pl.tip, da: at.d, db: dotOf(pl), go: at.t, land: c.tagAt, s: Math.max(at.s, c.T.s)});
    at = {p: pl.tip, d: dotOf(pl), t: c.go, s: c.T.s};
  });
  const R = plan.closer.route;
  const nodes = wallPills.filter((p): p is Pill => !!p);
  const wallLand = nodes.map((_, j) => R.at + (R.len * (j + 1)) / nodes.length);
  nodes.forEach((pl, j) => {
    legs.push({a: at.p, b: pl.tip, da: at.d, db: dotOf(pl), go: at.t, land: wallLand[j], s: Math.max(at.s, 0.5)});
    at = {p: pl.tip, d: dotOf(pl), t: wallLand[j], s: 0.5};
  });
  return {hookPills, cardPills, nodes, wallLand, G, gDot, legs};
};

export type Tags = ReturnType<typeof tagsOf>;

const flight = bezier([0.6, 0, 0.3, 1]);

/** Where the travelling dot is at beat `t` (null while it is open as a tag), and its diameter. */
export const dotAt = (tags: Tags, t: number): {p: THREE.Vector3; d: number} | null => {
  for (const g of tags.legs) {
    if (t < g.go || t >= g.land) continue;
    const u = flight(clamp01((t - g.go) / (g.land - g.go)));
    const p = g.a.clone().lerp(g.b, u);
    p.z += Math.sin(Math.PI * u) * 260 * g.s;
    return {p, d: lerp(g.da, g.db, u) * (1 + 0.4 * Math.sin(Math.PI * u))};
  }
  return null;
};

/** Where the tag is at beat `t` whatever its shape: for the dust it sweeps and the light it carries. */
export const tagAt = (plan: Plan, tags: Tags, t: number): THREE.Vector3 => {
  const d = dotAt(tags, t);
  if (d) return d.p;
  const leg = [...tags.legs].reverse().find((g) => t >= g.land);
  return leg ? leg.b.clone() : tags.G.clone();
};

const disc = new THREE.CircleGeometry(0.5, 40);

export const TagTrack: React.FC<{plan: Plan; tags: Tags; fonts: Fonts; t: number}> = ({plan, tags, fonts, t}) => {
  const [hook, ...people] = plan.cards;
  const dots = (n: number, order: number) => Array.from({length: n}, (_, i) => {
    const m = new THREE.Mesh(disc, new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false}));
    m.frustumCulled = false;
    m.renderOrder = order - i;
    return m;
  });
  const trail = useMemo(() => dots(TRAIL, 4000), []);
  const runners = useMemo(() => dots(tags.hookPills.length, 3990), [tags]);
  const gather = plan.gather;
  // the hook's tags: each opens on its head, then closes and runs into the one dot as the gather lands
  const hookViews = tags.hookPills.map((p, i) => {
    const at = hook.tagAt + i * hook.tagStep;
    if (t < at || t >= gather - 0.15) return null;
    const u = opening(t, at) * (1 - span(t, gather - 0.3, CLOSE));
    const shift = (p.tag.scroll ?? 0) * hook.T.s * Math.max(0, t - at);
    return <PillView key={`h${i}`} plan={plan} pill={p} u={u} fonts={fonts} order={3800 + i * 2} shift={shift} />;
  });
  const running = tags.hookPills.map((p, i) => {
    const u = span(t, gather - 0.15, 0.15, bezier([0.5, 0, 0.3, 1]));
    if (t < gather - 0.15 || t >= gather) return null;
    const m = runners[i];
    m.position.copy(p.tip.clone().lerp(tags.G, u));
    m.position.z += Math.sin(Math.PI * u) * 60 * hook.T.s;
    m.scale.setScalar(lerp(dotOf(p), tags.gDot, u));
    (m.material as THREE.MeshBasicMaterial).color.set(plan.colors.accent);
    return <primitive key={`r${i}`} object={m} />;
  });
  // the gathered dot, swelling as the tags meet, waiting for the camera to leave
  const held = t >= gather && t < hook.go;
  const swell = 1 + 0.35 * (1 - span(t, gather, 0.3));
  // each person's tag on their card, open from the moment the dot lands until it leaves
  const cardViews = people.map((c, i) => {
    const p = tags.cardPills[i];
    if (!p || t < c.tagAt || t >= c.go) return null;
    const u = opening(t, c.tagAt) * (1 - span(t, c.go - CLOSE, CLOSE));
    return <PillView key={`c${i}`} plan={plan} pill={p} u={u} fonts={fonts} order={3850 + i * 2} />;
  });
  // their tags on the wall, each left behind as the dot lands on it, the last opened by the still
  const last = tags.nodes.length - 1;
  const wallViews = tags.nodes.map((p, j) => {
    const land = tags.wallLand[j];
    const from = j === last ? land - OPEN : land - 0.08;
    if (t < from) return null;
    const u = j === last ? clamp01((t - from) / OPEN) : opening(t, from);
    return <PillView key={`w${j}`} plan={plan} pill={p} u={j === last ? bezier([0.2, 0.9, 0.3, 1])(u) : u} fonts={fonts} order={3900 + j * 2} />;
  });
  // the travelling dot and its trail
  const now = dotAt(tags, t) ?? (held ? {p: tags.G, d: tags.gDot * swell} : null);
  trail.forEach((m, i) => {
    const k = i === 0 ? now : dotAt(tags, t - i * 0.025);
    const mat = m.material as THREE.MeshBasicMaterial;
    mat.color.set(plan.colors.accent);
    if (!k || !now) {
      m.visible = false;
      return;
    }
    const fall = 1 - i / TRAIL;
    m.visible = i === 0 || k.p.distanceTo(now.p) > 2;
    m.position.copy(k.p);
    m.position.z -= i * 0.2;
    m.scale.setScalar(k.d * (i === 0 ? 1 : 0.85 * fall + 0.15));
    mat.opacity = i === 0 ? 1 : 0.5 * fall * fall;
  });
  return (
    <group>
      {hookViews}
      {running}
      {cardViews}
      {wallViews}
      {trail.map((m, i) => <primitive key={i} object={m} />)}
    </group>
  );
};
