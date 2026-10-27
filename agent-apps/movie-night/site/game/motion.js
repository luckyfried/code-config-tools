// The motion every view shares: springs, the wall's glide, the coverflow slot for a poster, and the fixed-step loop.

export const POSTER_W = 1.4;
export const POSTER_H = 2.1;
export const POSTER_BASE = 0.06;
export const FRONT_Z = 0.5;

// A damped spring on one number. zeta under 1 overshoots once and settles, which is what "squares up" looks like.
export function spring(s, target, k, zeta, dt) {
  const c = 2 * Math.sqrt(k) * zeta;
  s.v += (-k * (s.x - target) - c * s.v) * dt;
  s.x += s.v * dt;
}

// Where a poster sits when it is d places from the front: x and z in world units, rot the turn about its upright axis.
export function slot(d, phone) {
  const a = Math.abs(d);
  const s = Math.sign(d);
  const near = Math.min(a, 1);
  const far = Math.max(a - 1, 0);
  const spread = phone ? 1.08 : 1.24;
  const step = phone ? 0.46 : 0.58;
  return {
    x: s * (near * spread + far * step),
    z: FRONT_Z - near * 1.15 - far * 0.42,
    rot: -s * near * 0.96,
  };
}

// The wall's position along the list, in posters. A drag moves it directly; a release carries the flick's speed into a
// spring toward the poster the flick would reach, so the glide has inertia and lands squarely on one poster.
export class Glide {
  constructor() {
    this.p = 0;
    this.v = 0;
    this.target = 0;
    this.count = 1;
    this.dragging = false;
  }

  setCount(n) {
    this.count = Math.max(1, n);
    this.target = this.clamp(this.target);
  }

  clamp(i) {
    return Math.min(this.count - 1, Math.max(0, Math.round(i)));
  }

  get front() {
    return this.clamp(this.p);
  }

  jump(i) {
    this.p = i;
    this.v = 0;
  }

  go(i) {
    this.target = this.clamp(i);
  }

  nudge(step) {
    this.target = this.clamp((this.dragging ? this.p : this.target) + step);
  }

  grab() {
    this.dragging = true;
    this.v = 0;
  }

  drag(dp) {
    const over = this.p < 0 ? -this.p : this.p > this.count - 1 ? this.p - (this.count - 1) : 0;
    this.p += dp / (1 + over * 2.5);
  }

  release(velocity) {
    this.dragging = false;
    this.v = velocity;
    this.target = this.clamp(this.p + velocity * 0.3);
  }

  step(dt) {
    if (this.dragging) return;
    const s = { x: this.p, v: this.v };
    spring(s, this.target, 64, 0.78, dt);
    this.p = s.x;
    this.v = s.v;
  }

  settled() {
    return !this.dragging && Math.abs(this.p - this.target) < 0.002 && Math.abs(this.v) < 0.01;
  }
}

// Fixed 60 Hz updates with an accumulator, one render per animation frame, paused while the page is hidden.
export function startLoop(update, render) {
  const step = 1 / 60;
  let acc = 0;
  let last = performance.now();
  let raf = 0;
  const frame = (now) => {
    raf = requestAnimationFrame(frame);
    acc += Math.min((now - last) / 1000, 0.1);
    last = now;
    let n = 0;
    while (acc >= step && n < 4) {
      update(step);
      acc -= step;
      n += 1;
    }
    if (n === 4) acc = 0;
    render(now / 1000);
  };
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      cancelAnimationFrame(raf);
      raf = 0;
    } else if (!raf) {
      last = performance.now();
      raf = requestAnimationFrame(frame);
    }
  });
  raf = requestAnimationFrame(frame);
}

export const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
