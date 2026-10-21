// The dot: the one thing that travels the whole film. It waits at the start of a photograph's line while the
// photograph is seen, draws the line across it (the blade cuts behind it), rests at the line's end, then leaves with
// the camera and arcs to the start of the next photograph's line, which it draws in turn. It goes out as the bars rise.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, clamp01, lerp, span} from '../../system/three/motion';
import {liftOf} from './card';
import {onWall, type Plan} from './plan';

/** Beats the dot takes to draw a line, ending as the blade cuts (drive.py's SWEEP). */
const SWEEP = 0.3;
const TRAIL = 10;
const R = 22;

type Edge = {a: THREE.Vector3; b: THREE.Vector3; cut: number; arrive: number; leave: number; s: number; color: string};

export const edgesOf = (plan: Plan): Edge[] =>
  plan.cards.map((c) => {
    const w = (p: [number, number], z: number) => {
      const q = onWall(c.T, p);
      return new THREE.Vector3(q[0] - plan.W / 2, plan.H / 2 - q[1], z);
    };
    const z = liftOf(c) + 13 * c.T.s;
    const color = c.field === 'accent' ? plan.colors.paper : plan.colors.accent;
    return {a: w([0, c.line[0]], z), b: w([plan.W, c.line[1]], z), cut: c.cut, arrive: c.arrive, leave: c.leave, s: c.T.s, color};
  });

const sweepOf = (e: Edge) => (e.cut - SWEEP <= 0 ? [0, e.cut] : [e.cut - SWEEP, e.cut]);

/** Where the dot is at beat `t`, how strongly it shows (0 to 1), its radius (wall px), its colour, and how far along the
 * current card's line it has drawn (0 to 1, with the card's index). */
export const sparkAt = (edges: Edge[], t: number, end = Infinity): {p: THREE.Vector3; glow: number; size: number; color: THREE.Color; drawn: [number, number]} => {
  const sweep = bezier([0.45, 0, 0.25, 1]);
  const arc = bezier([0.6, 0, 0.3, 1]);
  const out = 1 - span(t, end, 0.4);
  for (let i = 0; i < edges.length; i++) {
    const e = edges[i];
    const next = edges[i + 1];
    const [s0, s1] = sweepOf(e);
    const col = new THREE.Color(e.color);
    if (t < s0) return {p: e.a.clone(), glow: out * (i === 0 ? span(t, -0.2, 0.2) : 1), size: R * e.s, color: col, drawn: [i, 0]};
    if (t < s1) {
      const u = sweep(clamp01((t - s0) / (s1 - s0)));
      return {p: e.a.clone().lerp(e.b, u), glow: out, size: R * e.s, color: col, drawn: [i, u]};
    }
    if (!next) return {p: e.b.clone(), glow: out, size: R * e.s, color: col, drawn: [i, 1]};
    const go = e.leave - 0.6;
    const land = next.arrive + 0.25;
    if (t < go) return {p: e.b.clone(), glow: out, size: R * e.s, color: col, drawn: [i, 1]};
    if (t < land) {
      const u = arc(clamp01((t - go) / (land - go)));
      const p = e.b.clone().lerp(next.a, u);
      p.z += Math.sin(Math.PI * u) * 260 * Math.max(e.s, next.s);
      return {p, glow: out, size: lerp(e.s, next.s, u) * R * (1 + 0.5 * Math.sin(Math.PI * u)), color: col.lerp(new THREE.Color(next.color), u), drawn: [i, 1]};
    }
  }
  const e = edges[edges.length - 1];
  return {p: e.b.clone(), glow: out, size: R * e.s, color: new THREE.Color(e.color), drawn: [edges.length - 1, 1]};
};

const disc = new THREE.CircleGeometry(1, 40);

export const Spark: React.FC<{plan: Plan; t: number; height: number}> = ({plan, t}) => {
  const edges = useMemo(() => edgesOf(plan), [plan]);
  const parts = useMemo(() => {
    const dots = Array.from({length: TRAIL}, (_, i) => {
      const m = new THREE.Mesh(disc, new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false}));
      m.frustumCulled = false;
      m.renderOrder = 4000 - i;
      return m;
    });
    const lineGeo = new THREE.PlaneGeometry(1, 1).translate(0.5, 0, 0);
    const line = new THREE.Mesh(lineGeo, new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false}));
    line.frustumCulled = false;
    line.renderOrder = 3990;
    return {dots, line};
  }, []);
  const end = plan.ribbon.at;
  const now = sparkAt(edges, t, end);
  if (now.glow <= 0.001) return null;
  parts.dots.forEach((m, i) => {
    const k = i === 0 ? now : sparkAt(edges, t - i * 0.025, end);
    const moved = k.p.distanceTo(now.p);
    const fall = 1 - i / TRAIL;
    const mat = m.material as THREE.MeshBasicMaterial;
    m.visible = i === 0 || moved > 2;
    m.position.copy(k.p);
    m.position.z -= i * 0.2;
    m.scale.setScalar(k.size * (i === 0 ? 1 : 0.85 * fall + 0.15));
    mat.color.copy(k.color);
    mat.opacity = k.glow * (i === 0 ? 1 : 0.5 * fall * fall);
  });
  // the line the dot has drawn on its card, kept until the camera leaves that card
  const [ci, drawn] = now.drawn;
  const e = edges[ci];
  const lineMat = parts.line.material as THREE.MeshBasicMaterial;
  const head = e.a.clone().lerp(e.b, drawn);
  const len = head.distanceTo(e.a);
  const fade = 1 - span(t, e.leave - 0.6, 0.3);
  parts.line.visible = drawn > 0 && fade > 0;
  parts.line.position.copy(e.a);
  parts.line.position.z -= 0.5;
  parts.line.rotation.set(0, 0, Math.atan2(e.b.y - e.a.y, e.b.x - e.a.x));
  parts.line.scale.set(Math.max(0.001, len), 5 * e.s, 1);
  lineMat.color.set(e.color);
  lineMat.opacity = now.glow * fade;
  return (
    <group>
      <primitive object={parts.line} />
      {parts.dots.map((m, i) => <primitive key={i} object={m} />)}
    </group>
  );
};

/** The closer's route: the dot rises as the full stop after the lowest count as the wall lands, then runs the
 * countdown across the wall, arcing toward the lens and landing as the full stop after each count in turn on the half
 * beat, swelling as it lands, and comes to rest as the full stop after the ask at the still. */
export const Route: React.FC<{plan: Plan; t: number; nodes: {p: THREE.Vector3; r: number}[]}> = ({plan, t, nodes}) => {
  const dots = useMemo(() => Array.from({length: TRAIL}, (_, i) => {
    const m = new THREE.Mesh(disc, new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, depthWrite: false}));
    m.frustumCulled = false;
    m.renderOrder = 3995 - i;
    return m;
  }), []);
  const C = plan.closer.at;
  const S = plan.closer.still;
  if (nodes.length < 2 || t < C - 0.15 || S <= C) return null;
  const hops = nodes.length - 1;
  const ease = bezier([0.55, 0, 0.25, 1]);
  const at = (tt: number) => {
    const u = clamp01((tt - C) / (S - C)) * hops;
    const k = Math.min(hops - 1, Math.floor(u));
    const f = u - k;
    const e = ease(f);
    const a = nodes[k], b = nodes[k + 1];
    const p = a.p.clone().lerp(b.p, e);
    p.z += Math.sin(Math.PI * e) * 220;
    const swell = Math.max(k === hops - 1 ? 0 : span(f, 0.8, 0.2), k === 0 ? 0 : 1 - span(f, 0, 0.2));
    return {p, r: lerp(a.r, b.r, e) * (1 + 0.5 * swell)};
  };
  const glow = span(t, C - 0.15, 0.15);
  const color = plan.closer.ground === 'accent' ? plan.colors.paper : plan.colors.accent;
  const now = at(t);
  dots.forEach((m, i) => {
    const k = i === 0 ? now : at(t - i * 0.025);
    const fall = 1 - i / TRAIL;
    m.visible = i === 0 || k.p.distanceTo(now.p) > 2;
    m.position.copy(k.p);
    m.position.z -= i * 0.2;
    m.scale.setScalar(k.r * (i === 0 ? 1 : 0.85 * fall + 0.15));
    const mat = m.material as THREE.MeshBasicMaterial;
    mat.color.set(color);
    mat.opacity = glow * (i === 0 ? 1 : 0.5 * fall * fall * (1 - span(t, S - 0.15, 0.15)));
  });
  return <group>{dots.map((m, i) => <primitive key={i} object={m} />)}</group>;
};
