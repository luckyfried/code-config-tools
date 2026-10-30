// The dot: the year, the one thing that travels the whole film. It stands on the first place's pin from the first
// frame, over the whole route; while a place's card stands open it waits under it on the pin, and as the card folds onto
// the map it runs the leg to the next place, drawing the route behind it. In the closer it rests on the last place's
// pin, swelling once as the closer lands. It draws over everything on the map it passes, never over an open card.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span} from '../../system/three/motion';
import {cardSpace} from './card';
import type {Plan} from './plan';

/** Beats after the camera leaves a place that the dot sets out along the leg. */
const SET_OUT = 0.15;
const TRAIL = 10;
/** The ring around the dot's core, as a multiple of the core's radius, and the dot's ring as a share of the picture's
 * height: one size on screen however far the camera is. */
const RING = 1.32;
const SIZE = 0.011;
const MAP_Z = 1.5;

const run = bezier([0.5, 0, 0.3, 1]);

/** The window the dot runs leg `i` in: from setting out to arriving at the next pin. */
export const legWindow = (plan: Plan, i: number): [number, number] => {
  const c = plan.cards[i];
  return [c.goAt + SET_OUT, c.leave - 0.05];
};

/** How far along leg `i` the dot has run at beat `t`, 0 to 1: the route is drawn this far. */
export const legDrawn = (plan: Plan, i: number, t: number) => {
  const [a, b] = legWindow(plan, i);
  return run(clamp01((t - a) / (b - a)));
};

const world = (plan: Plan, p: [number, number], z: number) => new THREE.Vector3(p[0] - plan.W / 2, plan.H / 2 - p[1], z);

const alongWorld = (plan: Plan, i: number, u: number) => {
  const leg = plan.legs[i];
  const total = leg.len[leg.len.length - 1];
  const d = u * total;
  let k = 1;
  while (k < leg.len.length - 1 && leg.len[k] < d) k++;
  const a = leg.pts[k - 1], b = leg.pts[k];
  const seg = leg.len[k] - leg.len[k - 1];
  const f = seg > 0 ? (d - leg.len[k - 1]) / seg : 0;
  return world(plan, [lerp(a[0], b[0], f), lerp(a[1], b[1], f)], MAP_Z);
};

/** Where the dot is at beat `t`, how strongly it shows (it waits unseen under an open card), and how much it swells. */
export const dotAt = (plan: Plan, t: number): {p: THREE.Vector3; glow: number; swell: number} => {
  const cards = plan.cards;
  for (let i = 0; i < cards.length; i++) {
    const c = cards[i];
    const [a, b] = plan.legs[i] ? legWindow(plan, i) : [Infinity, Infinity];
    if (t < a) {
      const open = cardSpace(plan, c, i, t).whole;
      const beat = i === 0 ? Math.sin(Math.PI * clamp01(t / 0.6)) * (1 - span(t, 0.6, 0.1)) : 0;
      return {p: world(plan, c.pin, MAP_Z), glow: 1 - open, swell: 0.5 * beat};
    }
    if (t < b) return {p: alongWorld(plan, i, legDrawn(plan, i, t)), glow: 1, swell: 0};
  }
  const last = cards[cards.length - 1];
  const age = t - (plan.closer.at + 0.25);
  return {p: world(plan, last.pin, MAP_Z), glow: 1, swell: age > 0 && age < 0.6 ? 0.45 * Math.sin((Math.PI * age) / 0.6) : 0};
};

const disc = new THREE.CircleGeometry(1, 48);

/** The dot and its trail, sized to the picture (`h` wall px tall) so it reads the same however far the camera is. */
export const Dot: React.FC<{plan: Plan; t: number; h: (t: number) => number; still: number}> = ({plan, t, h, still}) => {
  const parts = useMemo(() => {
    const mk = (order: number) => {
      const m = new THREE.Mesh(disc, new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false, depthTest: false}));
      m.frustumCulled = false;
      m.renderOrder = order;
      return m;
    };
    // over every print on the map and under the card the camera is on (route/card.tsx orders an open card from 500)
    return {ring: mk(451), core: mk(452), trail: Array.from({length: TRAIL}, (_, i) => mk(440 - i))};
  }, []);
  const tt = Math.min(t, still);
  const now = dotAt(plan, tt);
  if (now.glow <= 0.001) return null;
  const r = ((SIZE * h(tt)) / RING) * (1 + now.swell);
  const hot = new THREE.Color(plan.colors.route);
  parts.core.position.copy(now.p);
  parts.core.scale.setScalar(r);
  (parts.core.material as THREE.MeshBasicMaterial).color.copy(hot);
  (parts.core.material as THREE.MeshBasicMaterial).opacity = now.glow;
  parts.ring.position.copy(now.p).setZ(now.p.z - 0.05);
  parts.ring.scale.setScalar(r * RING);
  (parts.ring.material as THREE.MeshBasicMaterial).color.set(plan.colors.casing);
  (parts.ring.material as THREE.MeshBasicMaterial).opacity = now.glow;
  // the trail is one unbroken streak behind the dot: it ends at the first mark that would stand apart from the one
  // before it, so a fast move never leaves separate dots on the picture
  let prev = now.p;
  let broken = false;
  parts.trail.forEach((m, i) => {
    const k = dotAt(plan, tt - (i + 1) * 0.025);
    const fall = 1 - (i + 1) / (TRAIL + 1);
    const mat = m.material as THREE.MeshBasicMaterial;
    broken = broken || k.p.distanceTo(prev) > r * (0.85 * fall + 0.15);
    prev = k.p;
    m.visible = tt < still && !broken && k.p.distanceTo(now.p) > r * 0.3;
    m.position.copy(k.p).setZ(k.p.z - 0.1 - i * 0.02);
    m.scale.setScalar(r * (0.85 * fall + 0.15));
    mat.color.copy(hot);
    mat.opacity = k.glow * 0.5 * fall * fall;
  });
  return (
    <group>
      {parts.trail.map((m, i) => <primitive key={i} object={m} />)}
      <primitive object={parts.ring} />
      <primitive object={parts.core} />
    </group>
  );
};
