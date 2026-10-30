// The map the year is drawn on: the land the route crosses standing as a slab above the sea, lit from the upper left so
// its coasts throw a shadow on the water, on the film's paper where the card's finish has grain; the whole route laid
// faintly from the first frame, and drawn over it in the route's color on a casing of the color around it behind the
// dot leg by leg and kept, a constant width on screen however far the camera pulls back, swelling at the head where the
// dot is drawing it and settling behind; a pin at every place, set out one after another in the first beat.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, span, type Pt} from '../../system/three/motion';
import {paper, SHEET} from './paper';
import {along, type Plan} from './plan';

/** How deep the land stands above the sea, wall px. */
export const DEPTH = 22;

/** The land as a slab, its top at z 0, the coast line on it, and the land's outline that takes the prints' shadows. */
const useLand = (plan: Plan) =>
  useMemo(() => {
    const {W, H} = plan;
    const shapes: THREE.Shape[] = [];
    const coast: number[] = [];
    for (const ring of plan.land) {
      if (ring.length < 6) continue;
      const pts: THREE.Vector2[] = [];
      for (let i = 0; i < ring.length; i += 2) pts.push(new THREE.Vector2(ring[i] - W / 2, H / 2 - ring[i + 1]));
      shapes.push(new THREE.Shape(pts));
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], b = pts[(i + 1) % pts.length];
        coast.push(a.x, a.y, 0, b.x, b.y, 0);
      }
    }
    const slabGeo = new THREE.ExtrudeGeometry(shapes, {depth: DEPTH, bevelEnabled: false, curveSegments: 1});
    // the cap's texture coordinates are its wall px, so the paper tiles every SHEET px of the map
    const grained = plan.grain > 0;
    const top = new THREE.MeshBasicMaterial({color: new THREE.Color(plan.colors.land).multiplyScalar(grained ? 1.07 : 1), map: grained ? paper(1 / SHEET) : null, toneMapped: false});
    const side = new THREE.MeshBasicMaterial({color: plan.colors.side, toneMapped: false});
    const slab = new THREE.Mesh(slabGeo, [top, side]);
    slab.position.z = -DEPTH;
    // only a grained (paper) map stands off the sea and casts a shadow; a flat one is printed flat
    slab.castShadow = plan.grain > 0;
    slab.renderOrder = -9;
    slab.frustumCulled = false;
    const catcher = new THREE.Mesh(new THREE.ShapeGeometry(shapes), new THREE.ShadowMaterial({opacity: 0.3, transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -8}));
    catcher.position.z = 0.05;
    catcher.receiveShadow = true;
    catcher.renderOrder = -8;
    catcher.frustumCulled = false;
    const cg = new THREE.BufferGeometry();
    cg.setAttribute('position', new THREE.Float32BufferAttribute(coast, 3));
    const lines = new THREE.LineSegments(cg, new THREE.LineBasicMaterial({color: plan.colors.coast, toneMapped: false, depthWrite: false, transparent: true, opacity: 0.8}));
    lines.position.z = 0.15;
    lines.renderOrder = -7;
    lines.frustumCulled = false;
    return {slab, catcher, lines};
  }, [plan]);

/** How far along leg `i` the route is drawn at beat `t`, 0 to 1. */
export type Drawn = (i: number, t: number) => number;

const MAX = 4096;

/** A strip of quads the route is drawn into each frame. */
const useStrip = (color: string, order: number) =>
  useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(MAX * 12), 3));
    const idx: number[] = [];
    for (let i = 0; i < MAX; i++) idx.push(4 * i, 4 * i + 1, 4 * i + 2, 4 * i + 2, 4 * i + 1, 4 * i + 3);
    geo.setIndex(idx);
    const mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({color, toneMapped: false, depthWrite: false, depthTest: false, side: THREE.DoubleSide}));
    mesh.frustumCulled = false;
    mesh.renderOrder = order;
    return {geo, mesh};
  }, [color, order]);

/** How much wider the line is at the head the dot is drawing, and over how many line widths behind it that settles. */
const SWELL = 0.8;
const SETTLE = 9;

/** Draws the drawn part of every leg into a strip, as quads `width` wall px wide with closed joins, wider toward the head
 * of a leg the dot is still drawing. */
const drawRoute = (plan: Plan, strip: {geo: THREE.BufferGeometry}, t: number, drawn: Drawn, base: number, z: number) => {
  const {W, H} = plan;
  const pos = strip.geo.getAttribute('position') as THREE.BufferAttribute;
  let q = 0;
  const seg = (a: Pt, b: Pt, width: number) => {
    if (q >= MAX) return;
    const ax = a[0] - W / 2, ay = H / 2 - a[1], bx = b[0] - W / 2, by = H / 2 - b[1];
    const dx = bx - ax, dy = by - ay;
    const len = Math.hypot(dx, dy);
    if (len < 1e-6) return;
    const ux = dx / len, uy = dy / len;
    const nx = (-uy * width) / 2, ny = (ux * width) / 2;
    const ex = (ux * width) / 2, ey = (uy * width) / 2;
    pos.setXYZ(4 * q, ax - ex + nx, ay - ey + ny, z);
    pos.setXYZ(4 * q + 1, ax - ex - nx, ay - ey - ny, z);
    pos.setXYZ(4 * q + 2, bx + ex + nx, by + ey + ny, z);
    pos.setXYZ(4 * q + 3, bx + ex - nx, by + ey - ny, z);
    q++;
  };
  plan.legs.forEach((leg, i) => {
    const u = drawn(i, t);
    if (u <= 0) return;
    const d = u * leg.len[leg.len.length - 1];
    for (let k = 1; k < leg.pts.length; k++) {
      if (leg.len[k - 1] >= d) break;
      const behind = d - Math.min(leg.len[k], d);
      const width = base * (u < 1 ? 1 + SWELL * Math.exp(-behind / (SETTLE * base)) : 1);
      seg(leg.pts[k - 1], leg.len[k] <= d ? leg.pts[k] : along(leg, u), width);
    }
  });
  for (let k = q; k < MAX && k < q + 8; k++) for (let j = 0; j < 4; j++) pos.setXYZ(4 * k + j, 0, 0, -50);
  strip.geo.setDrawRange(0, q * 6);
  pos.needsUpdate = true;
};

const disc = new THREE.CircleGeometry(1, 40);

/** The beat a place's pin is set out on the map: one after another in the film's first beat, so the whole way reads
 * from the first second. */
export const pinFrom = (plan: Plan, i: number) => Math.min(0.6, (0.6 * i) / Math.max(1, plan.cards.length - 1)) - 0.25;

/** How far the whole route under the part the dot has drawn leans from the land's color toward the route's. It is drawn
 * opaque in that mixed color, so the joins where its quads overlap never darken. */
const GHOST = 0.4;

/** Every place's pin, set out with a small overshoot. */
const Pins: React.FC<{plan: Plan; t: number}> = ({plan, t}) => {
  const parts = useMemo(() => plan.cards.map((_, i) => {
    const mk = (color: string, order: number) => {
      const m = new THREE.Mesh(disc, new THREE.MeshBasicMaterial({color, toneMapped: false, depthWrite: false, transparent: true}));
      m.frustumCulled = false;
      m.renderOrder = order;
      return m;
    };
    return {ring: mk(plan.colors.route, -3 + i * 0.01), core: mk(plan.colors.casing, -2.9 + i * 0.01)};
  }), [plan]);
  const r = plan.pin * 0.13;
  const pop = bezier([0.3, 1.6, 0.5, 1]);
  return (
    <group>
      {plan.cards.map((c, i) => {
        const on = pop(span(t, pinFrom(plan, i), 0.25, (u) => u));
        if (on <= 0.001) return null;
        const p = parts[i];
        const x = c.pin[0] - plan.W / 2, y = plan.H / 2 - c.pin[1];
        const k = r * on;
        p.ring.position.set(x, y, 0.4);
        p.ring.scale.setScalar(k);
        p.core.position.set(x, y, 0.5);
        p.core.scale.setScalar(k * 0.55);
        return (
          <group key={c.id}>
            <primitive object={p.ring} />
            <primitive object={p.core} />
          </group>
        );
      })}
    </group>
  );
};

export const MapView: React.FC<{plan: Plan; t: number; drawn: Drawn; h: number}> = ({plan, t, drawn, h}) => {
  const {slab, catcher, lines} = useLand(plan);
  const sea = useMemo(() => (plan.grain > 0 ? paper(400000 / SHEET) : null), [plan]);
  const faint = useMemo(() => '#' + new THREE.Color(plan.colors.land).lerp(new THREE.Color(plan.colors.route), GHOST).getHexString(), [plan]);
  const ghost = useStrip(faint, -6.5);
  const casing = useStrip(plan.colors.casing, -6);
  const core = useStrip(plan.colors.route, -5);
  drawRoute(plan, ghost, t, () => 1, h * 0.0045, 0.15);
  drawRoute(plan, casing, t, drawn, h * 0.015, 0.2);
  drawRoute(plan, core, t, drawn, h * 0.0085, 0.3);
  return (
    <group>
      <mesh position={[0, 0, -DEPTH]} renderOrder={-10}>
        <planeGeometry args={[400000, 400000]} />
        <meshBasicMaterial color={new THREE.Color(plan.colors.sea).multiplyScalar(sea ? 1.07 : 1)} map={sea} toneMapped={false} />
      </mesh>
      <mesh position={[0, 0, -DEPTH + 2]} receiveShadow renderOrder={-9.5}>
        <planeGeometry args={[400000, 400000]} />
        <shadowMaterial opacity={0.42} transparent depthWrite={false} />
      </mesh>
      <primitive object={slab} />
      <primitive object={catcher} />
      <primitive object={lines} />
      <primitive object={ghost.mesh} />
      <primitive object={casing.mesh} />
      <primitive object={core.mesh} />
      <Pins plan={plan} t={t} />
    </group>
  );
};
