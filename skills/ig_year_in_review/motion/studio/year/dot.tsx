// The dot: the one thing that travels the whole film. It draws the title's underline, arcs from its end to the year's
// full stop as the line drops open into the window, sits there while the months flash, arcs to the first month and
// draws each month's line across its photograph, waits at the line's end and arcs on to the next month's line as the
// next photograph opens, rides the last month's slit into its row, and in the closer flies back to the underline's end
// and draws one accent spine down the rows' ends, joining the year's line and every month's line into one figure, the
// full stop after each month's chapter, before it lands as the full stop of the sign-off.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span, type Pt} from '../../system/three/motion';
import {windowAt} from './hook';
import {REACH} from './month';
import {layerOf, lineY, liftOf, onWall, type Month, type Plan} from './plan';

export const TRAIL = 10;
const START = -60;

export type Dot = {p: THREE.Vector3; r: number; glow: number};

const at = (plan: Plan, q: Pt, z: number) => new THREE.Vector3(q[0] - plan.W / 2, plan.H / 2 - q[1], z);
const sweep = bezier([0.45, 0, 0.25, 1]);
const arc = bezier([0.6, 0, 0.3, 1]);
const hop = bezier([0.55, 0, 0.25, 1]);
const land = bezier([0.5, 0, 0.9, 0.5]);

/** A month line's two ends in world space, at the height the dot draws it; given a beat, on the photograph's near
 * layer as it stands then, which carries the line. */
export const endsOf = (plan: Plan, m: Month, t?: number) => {
  const {T, z} = t === undefined ? {T: m.T, z: liftOf(m)} : layerOf(plan, m, t);
  const end = (x: number) => at(plan, onWall(T, [x, lineY(m, plan.W, x)]), z + 13 * m.T.s);
  return [end(-REACH * plan.W), end((1 + REACH) * plan.W)];
};

/** Where the dot rests: the year's full stop, the end of each month's row, then the sign-off's full stop. */
export type Route = {title: {p: THREE.Vector3; r: number}; ends: THREE.Vector3[]; stop: {p: THREE.Vector3; r: number}};

const R_MONTH = 22;
const R_WALL = 7;
// the closer's lead into its hops: the flight up to the underline's end, then the drop down the spine to January's row
const LEAD = 0.9;
const RISE = 0.55;

const flight = (a: THREE.Vector3, b: THREE.Vector3, u: number, bump: number) => {
  const p = a.clone().lerp(b, u);
  p.z += Math.sin(Math.PI * u) * bump;
  return p;
};

/** Where the dot is at beat `t`. */
export const dotAt = (plan: Plan, t: number, route: Route): Dot => {
  const {ends, stop} = route;
  const [x0, y0, x1] = plan.rule;
  const ms = plan.months;
  const glow = span(t, -0.05, 0.08);
  const first = ms[0];
  if (t < 0.4) return {p: at(plan, [lerp(START, x1, sweep(clamp01(t / 0.4))), y0], 3), r: 9, glow};
  const [f0] = plan.hook.flash;
  const [c0] = plan.hook.close;
  const title = route.title;
  if (t < c0) {
    // from the underline's end to the year's full stop, there by the first flash, where it sits while the months flash
    const u = arc(clamp01((t - 0.4) / (f0 - 0.4)));
    return {p: flight(at(plan, [x1, y0], 3), title.p, u, 160), r: lerp(9, title.r, u), glow};
  }
  const [s0] = endsOf(plan, first);
  if (t < first.at.draw[0]) {
    // the dot leaves the year for the first month's line
    const u = arc(clamp01((t - c0) / (first.at.draw[0] - c0)));
    return {p: flight(title.p, s0, u, 420), r: lerp(title.r, R_MONTH * first.T.s, u) * (1 + 0.6 * Math.sin(Math.PI * u)), glow};
  }
  for (let i = 0; i < ms.length; i++) {
    const m = ms[i];
    const next = ms[i + 1];
    const [a, b] = endsOf(plan, m);
    const r = R_MONTH * m.T.s;
    const [d0, dl] = m.at.draw;
    if (t < d0 + dl) return {p: a.clone().lerp(b, sweep(clamp01((t - d0) / dl))), r, glow};
    if (next) {
      // it waits at the line's end and leaves for the next month's line as the next photograph opens over this one
      const go = m.at.pull[0];
      if (t < go) return {p: endsOf(plan, m, t)[1], r, glow};
      const [n0] = endsOf(plan, next);
      if (t < next.at.draw[0]) {
        const u = arc(clamp01((t - go) / (next.at.draw[0] - go)));
        return {p: flight(b, n0, u, 260 * next.T.s), r: lerp(r, R_MONTH * next.T.s, u) * (1 + 0.5 * Math.sin(Math.PI * u)), glow};
      }
      continue;
    }
    // the last month: it rides the slit's end into the last row
    const [sl0, sll] = m.at.slide;
    if (t < sl0) return {p: endsOf(plan, m, t)[1], r, glow};
    const bar = ends[i];
    if (t < sl0 + sll) {
      const u = bezier(plan.ease.move)(clamp01((t - sl0) / sll));
      return {p: b.clone().lerp(bar, u), r: lerp(r, R_WALL, u), glow};
    }
    // the closer: up to the underline's end, down the spine to the first row's end, down the rows, and on to the
    // sign-off's full stop
    const hops = plan.closer.hops;
    const lead = hops[0] - LEAD;
    if (t < lead) return {p: bar, r: R_WALL, glow};
    const top = at(plan, [x1, y0], 3);
    if (t < lead + RISE) {
      const u = arc(clamp01((t - lead) / RISE));
      return {p: flight(bar, top, u, 300), r: R_WALL * (1 + 0.6 * Math.sin(Math.PI * u)), glow};
    }
    if (t < hops[0]) return {p: top.clone().lerp(ends[0], sweep(clamp01((t - lead - RISE) / (LEAD - RISE)))), r: R_WALL, glow};
    for (let j = 1; j < hops.length; j++) {
      if (t < hops[j]) {
        const u = hop(clamp01((t - hops[j - 1]) / (hops[j] - hops[j - 1])));
        return {p: flight(ends[j - 1], ends[j], u, 120), r: R_WALL * (1 + 0.5 * Math.sin(Math.PI * u)), glow};
      }
    }
    const S = plan.closer.still;
    if (t < S) {
      // the last hop lands hard, still moving on the frame before it stops, the stop's hit on its landing
      const u = land(clamp01((t - hops[hops.length - 1]) / (S - hops[hops.length - 1])));
      return {p: flight(ends[ends.length - 1], stop.p, u, 260), r: lerp(R_WALL, stop.r, u) * (1 + 0.5 * Math.sin(Math.PI * u)), glow};
    }
    return {p: stop.p, r: stop.r, glow};
  }
  return {p: stop.p, r: stop.r, glow};
};

/** The spine's two ends in world space at beat `t`, the dot at `now`: from the underline's end down to the dot as it
 * drops down the rows' ends, then whole to the last row; none before the dot starts it. */
const spineAt = (plan: Plan, t: number, now: Dot): [THREE.Vector3, THREE.Vector3] | null => {
  if (t < plan.closer.hops[0] - LEAD + RISE) return null;
  const [, y0, x1] = plan.rule;
  const w = (y: number) => new THREE.Vector3(x1 - plan.W / 2, plan.H / 2 - y, 2.6);
  const last = plan.rows[plan.rows.length - 1].rule;
  const foot = Math.min(last, Math.max(y0, plan.H / 2 - now.p.y));
  return [w(y0 - 3), w(t < plan.closer.hops[plan.closer.hops.length - 1] ? foot : last)];
};

const disc = new THREE.CircleGeometry(1, 40);
const bar = new THREE.PlaneGeometry(1, 1).translate(0.5, 0, 0);

const lineMesh = (order: number) => {
  const m = new THREE.Mesh(bar, new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false}));
  m.frustumCulled = false;
  m.renderOrder = order;
  return m;
};

/** Lays a line mesh from `a` to `b`, `thick` wall px. */
const setLine = (m: THREE.Mesh, a: THREE.Vector3, b: THREE.Vector3, thick: number, color: THREE.Color, alpha: number) => {
  const len = Math.hypot(b.x - a.x, b.y - a.y);
  m.visible = alpha > 0.002 && len > 0.5;
  m.position.copy(a);
  m.rotation.set(0, 0, Math.atan2(b.y - a.y, b.x - a.x));
  m.scale.set(Math.max(0.001, len), thick, 1);
  const mat = m.material as THREE.MeshBasicMaterial;
  mat.color.copy(color);
  mat.opacity = alpha;
};

/** The dot, its trail, and every line it draws: the underline, the window's lower edge and each month's line as it is
 * drawn. From beat `upTo` on the dot and its trail are drawn over the card instead (card.tsx); the lines stay under it. */
export const DotView: React.FC<{plan: Plan; t: number; route: Route; upTo?: number}> = ({plan, t, route, upTo = Infinity}) => {
  const parts = useMemo(() => ({
    dots: Array.from({length: TRAIL}, (_, i) => {
      const m = new THREE.Mesh(disc, new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false}));
      m.frustumCulled = false;
      m.renderOrder = 4000 - i;
      return m;
    }),
    rule: lineMesh(3900), edge: lineMesh(3900), drawn: lineMesh(3901), spine: lineMesh(3900),
  }), []);
  const accent = new THREE.Color(plan.colors.accent);
  const hot = accent.clone().multiplyScalar(1.5);
  const now = dotAt(plan, t, route);
  parts.dots.forEach((m, i) => {
    const k = i === 0 ? now : dotAt(plan, t - i * 0.025, route);
    const fall = 1 - i / TRAIL;
    const mat = m.material as THREE.MeshBasicMaterial;
    // the trail is the dot's motion: once it has landed as the sign-off's full stop there is none
    m.visible = t < upTo && (i === 0 || (k.p.distanceTo(now.p) > 2 && t < Math.round(plan.closer.still * plan.pulse) / plan.pulse));
    m.position.copy(k.p);
    m.position.z += 0.4 - i * 0.02;
    m.scale.setScalar(k.r * (i === 0 ? 1 : 0.85 * fall + 0.15));
    mat.color.copy(i === 0 ? hot : accent);
    mat.opacity = k.glow * (i === 0 ? 1 : 0.5 * fall * fall);
  });
  // the underline: drawn by the dot, it stays under the year all film
  const [x0, y0, x1] = plan.rule;
  const w = (x: number, y: number, z: number) => new THREE.Vector3(x - plan.W / 2, plan.H / 2 - y, z);
  const ruleEnd = Math.min(x1, plan.W / 2 + now.p.x);
  setLine(parts.rule, w(x0, y0, 2.6), w(t < 0.4 ? Math.max(x0, ruleEnd) : x1, y0, 2.6), 6, accent, t < 0 ? 0 : 1);
  const win = windowAt(plan, t);
  setLine(parts.edge, w(x0, win.edge, 2.6), w(x1, win.edge, 2.6), 6, accent, win.open > 0.002 ? 1 : 0);
  // the spine: the dot draws it down the rows' ends from the underline's end, and it stays, so the year's line and every
  // month's line are one figure
  const spine = spineAt(plan, t, now);
  parts.spine.visible = false;
  if (spine) setLine(parts.spine, spine[0], spine[1], 6, accent, 1);
  // the month's line while the dot draws it; from the moment it is finished the month's own photograph carries it
  const m = [...plan.months].reverse().find((mm) => t >= mm.at.draw[0]);
  parts.drawn.visible = false;
  if (m && t < m.at.part[0] + 0.05) {
    const [a, b] = endsOf(plan, m);
    const head = t < m.at.draw[0] + m.at.draw[1] ? now.p : b;
    setLine(parts.drawn, a.clone().setZ(a.z - 0.5), head.clone().setZ(a.z - 0.5), 12 * m.T.s, accent, 1);
  }
  return (
    <group>
      <primitive object={parts.rule} />
      <primitive object={parts.edge} />
      <primitive object={parts.spine} />
      <primitive object={parts.drawn} />
      {parts.dots.map((d, i) => <primitive key={i} object={d} />)}
    </group>
  );
};
