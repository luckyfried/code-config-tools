// Springs and curves shared by the scene. A spring settles a value toward its target with a little overshoot;
// the curves shape the timed moves (a book flying to its slot, floating to the camera, the cover opening).
export const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const damp = (current, target, rate, dt) => lerp(current, target, 1 - Math.exp(-rate * dt));

export const ease = {
  outCubic: (t) => 1 - (1 - t) ** 3,
  outQuint: (t) => 1 - (1 - t) ** 5,
  inOutCubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2),
  inOutQuart: (t) => (t < 0.5 ? 8 * t ** 4 : 1 - (-2 * t + 2) ** 4 / 2),
  outBack: (t) => {
    const c1 = 1.4;
    const c3 = c1 + 1;
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2;
  },
};

export class Spring {
  constructor(stiffness = 260, ratio = 0.62) {
    this.k = stiffness;
    this.c = 2 * Math.sqrt(stiffness) * ratio;
    this.x = 0;
    this.v = 0;
    this.target = 0;
  }

  snap(value) {
    this.x = value;
    this.v = 0;
    this.target = value;
  }

  get resting() {
    return Math.abs(this.x - this.target) < 1e-4 && Math.abs(this.v) < 1e-3;
  }

  step(dt) {
    let left = Math.min(dt, 0.1);
    while (left > 0) {
      const h = Math.min(left, 1 / 120);
      const a = -this.k * (this.x - this.target) - this.c * this.v;
      this.v += a * h;
      this.x += this.v * h;
      left -= h;
    }
    if (this.resting) this.snap(this.target);
    return this.x;
  }
}

/** True when the person asked the system for less motion; read live so a change applies at once. */
const reduceQuery = typeof matchMedia === "function" ? matchMedia("(prefers-reduced-motion: reduce)") : null;
export const reducedMotion = () => Boolean(reduceQuery && reduceQuery.matches);
