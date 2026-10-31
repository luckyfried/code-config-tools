// The hook's window: the underline the dot draws drops open into a window as wide as the type area, the months'
// photographs flash through it, the look's lead first, each as long as the next, its edges catching the light, and it
// shuts once the first month's photograph fills the picture.
import {useMemo} from 'react';
import * as THREE from 'three';
import {bezier, span, type Pt} from '../../system/three/motion';
import {framingAt} from './camera';
import {lit, quad, setQuad} from './month';
import type {Month, Plan} from './plan';

/** How open the window is at beat `t` (0 shut, 1 open), and the y of its lower edge on the wall. */
export const windowAt = (plan: Plan, t: number) => {
  const [, y0, , y1] = plan.hook.window;
  const open = span(t, 0.4, plan.hook.flash[0] - 0.4, bezier([0.3, 0, 0.2, 1])) * (1 - span(t, plan.months[0].at.arrive, 0.5));
  return {open, edge: y0 + (y1 - y0) * open};
};

/** Which month's photograph the window shows at beat `t` (its index in `plan.months`, from the hook's flash order),
 * and how far into its flash. */
export const flashAt = (plan: Plan, t: number) => {
  const f = plan.hook.flash;
  const i = Math.max(0, Math.min(plan.months.length - 1, f.filter((b) => t >= b).length - 1));
  return {k: plan.hook.order[i], u: Math.max(0, Math.min(1, (t - f[i]) / (f[i + 1] - f[i])))};
};

/** The photograph's texture window that covers a w by h box around its focus, scaled in by `zoom`. */
export const coverUv = (m: Month, w: number, h: number, zoom: number): [Pt, Pt] => {
  const [pw, ph] = m.size;
  const k = Math.max(w / pw, h / ph) * zoom;
  const uw = w / (pw * k), uh = h / (ph * k);
  const u0 = Math.min(1 - uw, Math.max(0, m.focus[0] - uw / 2));
  const v0 = Math.min(1 - uh, Math.max(0, m.focus[1] - uh / 2));
  return [[u0, 1 - v0], [u0 + uw, 1 - v0 - uh]];
};

/** The texture window of month `m`'s photograph in the hook's window at beat `t`, `u` into its flash, and the lowest wall
 * y it reaches: the photograph covers the part of the window the camera shows at `t` (the window's top part while the
 * camera holds on the year, all of it once the camera has dived in), its focus in that part's middle, and settles in a
 * little as it flashes. */
export const hookUv = (plan: Plan, m: Month, t: number, u: number): {uv: [Pt, Pt]; foot: number} => {
  const [x0, y0, x1, y1] = plan.hook.window;
  const f = framingAt(plan, t).framing;
  const foot = Math.min(y1, Math.max(y0 + 100, f.c[1] + f.h / 2 + 40));
  return {uv: coverUv(m, x1 - x0, foot - y0, 1.12 - 0.12 * bezier([0.2, 0.8, 0.3, 1])(u)), foot};
};

export const HookWindow: React.FC<{plan: Plan; t: number; textures: (m: Month) => THREE.Texture}> = ({plan, t, textures}) => {
  const q = useMemo(() => quad(lit(new THREE.MeshBasicMaterial({toneMapped: false, transparent: true, side: THREE.DoubleSide}))), []);
  const {open, edge} = windowAt(plan, t);
  if (open <= 0.001) return null;
  const [x0, y0, x1] = plan.hook.window;
  const {k, u} = flashAt(plan, t);
  const m = plan.months[k];
  const {uv: [a, b], foot} = hookUv(plan, m, t, u);
  // the window's photograph is pinned to the wall: opening uncovers it downward rather than squeezing it, and below
  // what the camera shows the window is not drawn
  const bottom = Math.min(edge, foot);
  const vEdge = a[1] + ((b[1] - a[1]) * (bottom - y0)) / (foot - y0);
  const w = (p: Pt) => new THREE.Vector3(p[0] - plan.W / 2, plan.H / 2 - p[1], 1);
  setQuad(q, [w([x0, y0]), w([x1, y0]), w([x1, bottom]), w([x0, bottom])], [[a[0], a[1]], [b[0], a[1]], [b[0], vEdge], [a[0], vEdge]]);
  const mat = q.mesh.material as THREE.MeshBasicMaterial;
  mat.map = textures(m);
  mat.color.setScalar(1 + 0.35 * (1 - span(u, 0, 0.5)));
  mat.needsUpdate = mat.map !== (q.mesh.userData.map as THREE.Texture | undefined);
  q.mesh.userData.map = mat.map;
  q.mesh.renderOrder = 50;
  return <primitive object={q.mesh} />;
};
