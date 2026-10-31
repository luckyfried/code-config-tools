// The motion the spectacle moves time themselves by, in seconds so a move feels the same at any tempo: a damped spring
// solved in closed form, and a screen shake that dies away after a hit.

/** Seconds per musical beat on this film. */
export const secondsOf = (look: {pulse: number; fps: number}, beats: number) => (beats * look.pulse) / look.fps;

/** A damped spring released from 0 toward rest at 1, `t` seconds after release, with stiffness `k` and damping `c` on a
 * unit mass. Under critical damping (c < 2 sqrt k) it overshoots and rings down; at or over it, it eases in without
 * passing 1. */
export const spring = (t: number, k = 170, c = 16) => {
  if (t <= 0) return 0;
  const w = Math.sqrt(k);
  const z = c / (2 * w);
  if (z >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const wd = w * Math.sqrt(1 - z * z);
  return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + ((z * w) / wd) * Math.sin(wd * t));
};

/** The frame's offset `t` seconds after a hit: x and y in px and a turn in degrees, `amp` px at the hit and falling by
 * a factor of e every `tau` seconds; still before the hit and once it has died away. */
export const shake = (t: number, seed: number, amp: number, tau = 0.08) => {
  if (t < 0 || t > tau * 7) return {x: 0, y: 0, r: 0};
  const a = amp * Math.exp(-t / tau);
  const f = 2 * Math.PI * 26;
  return {
    x: a * Math.sin(f * t + seed * 1.7),
    y: a * 0.7 * Math.sin(f * 1.31 * t + seed * 4.3),
    r: a * 0.015 * Math.sin(f * 0.77 * t + seed * 2.9),
  };
};
