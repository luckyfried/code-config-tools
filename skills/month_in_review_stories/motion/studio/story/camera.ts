// A story card's one camera: each shot a hold from its view toward where it ends (a slow push, or its `to`), and between
// shots an eased move that pulls back or pushes in by the shot's arc and, on a card whose ground reaches past the frame,
// banks and looks ahead along the travel. The card opens slightly pushed in and settles out to its first view.
import type {Pose} from '../../system/three/Stage';
import {bezier, clamp01, lerp, span} from '../../system/three/motion';
import type {Travel} from '../../system/three/travel';
import {heldOf, startsOf, type Card, type View} from './plan';

export const W = 1080;
export const H = 1920;
const FOV = 30;
const MOVE = bezier([0.7, 0, 0.2, 1]);
const OPEN = bezier([0.2, 0.9, 0.3, 1]);

type Framing = View & {fov: number};

export const poseOf = (f: Framing): Pose => {
  const target: [number, number, number] = [f.c[0] - W / 2, H / 2 - f.c[1], 0];
  const D = f.h / 2 / Math.tan((f.fov * Math.PI) / 360);
  const cp = Math.cos(f.pitch);
  return {
    position: [target[0] + D * Math.sin(f.yaw) * cp, target[1] - D * Math.sin(f.pitch), target[2] + D * Math.cos(f.yaw) * cp],
    target, roll: f.roll, fov: f.fov,
  };
};

const mixF = (a: Framing, b: Framing, u: number): Framing => ({
  c: [lerp(a.c[0], b.c[0], u), lerp(a.c[1], b.c[1], u)], h: a.h * Math.pow(b.h / a.h, u), fov: lerp(a.fov, b.fov, u),
  yaw: lerp(a.yaw, b.yaw, u), pitch: lerp(a.pitch, b.pitch, u), roll: lerp(a.roll, b.roll, u),
});

const F = (v: View): Framing => ({...v, fov: FOV});

/** The move from `a` to `b` at eased progress `u`: it pulls back by `arc` at its middle (pushes in when negative) and,
 * by `bank`, banks and looks ahead along the travel. */
const travel = (a: Framing, b: Framing, u: number, arc: number, bank: number): Framing => {
  const m = mixF(a, b, u);
  const bell = Math.sin(Math.PI * u);
  const scale = Math.max(a.h, b.h);
  const lx = Math.max(-1, Math.min(1, (b.c[0] - a.c[0]) / scale));
  const ly = Math.max(-1, Math.min(1, (b.c[1] - a.c[1]) / scale));
  return {
    ...m, h: m.h * (1 + arc * bell), yaw: m.yaw - bank * 0.42 * lx * bell, pitch: m.pitch - bank * 0.3 * ly * bell,
    roll: m.roll + bank * (0.1 * lx + 0.05) * bell, fov: m.fov + 8 * bank * bell,
  };
};

export const framingAt = (c: Card, t: number): Framing => {
  const s = startsOf(c);
  const [out, inn] = c.move;
  const n = c.shots.length;
  const end = c.shots.map((sh, i) => s[i] + sh.beats);
  for (let i = 0; i < n; i++) {
    const sh = c.shots[i];
    const a = i === 0 ? 0 : s[i] + inn;
    const b = i + 1 < n ? end[i] - out : end[i];
    if (t < b || i === n - 1) {
      if (i > 0 && t < a) {
        // the move into shot i
        const from = F(heldOf(c.shots[i - 1]));
        const to = F(sh.view);
        const u = MOVE(clamp01((t - (s[i] - out)) / (out + inn)));
        const far = Math.hypot(to.c[0] - from.c[0], to.c[1] - from.c[1]) / Math.max(from.h, to.h);
        const arc = sh.arc ?? Math.min(0.3, 0.12 + 0.3 * Math.min(1, far));
        return travel(from, to, u, arc, c.bank);
      }
      const k = clamp01((t - a) / Math.max(0.1, b - a));
      const f = mixF(F(sh.view), F(heldOf(sh)), sh.to ? span(k, 0, 1) : k);
      if (i === 0) return {...f, h: f.h * (1 - 0.08 * (1 - span(t, 0, 0.5, OPEN)))};
      return f;
    }
  }
  return F(c.shots[n - 1].view);
};

// the cards carry their cuts on the camera's move alone: the travel pass draws no blur or warp, only the vignette
const CLEAR: Travel = {zoom: 0, center: [0.5, 0.5], smear: [0, 0], warp: 0, vignette: 0.2, time: 0};

/** The pose at beat `t`, and the travel pass the stage draws it through. */
export const shotAt = (c: Card, t: number): {pose: Pose; travel: Travel} => ({pose: poseOf(framingAt(c, t)), travel: CLEAR});
