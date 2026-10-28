// Every shard in flight, as flat typed arrays: position, heading, speed easing toward a target, turn rate, spin, size,
// and color. Live shards sit in [0, count); a removed shard swaps with the last, so the instanced mesh draws `count`.
export const GRAZED = 1;

export class BulletPool {
  constructor(capacity) {
    this.capacity = capacity;
    this.limit = capacity;
    this.count = 0;
    const f = () => new Float32Array(capacity);
    this.x = f();
    this.y = f();
    this.h = f();
    this.cos = f();
    this.sin = f();
    this.s = f();
    this.st = f();
    this.sk = f();
    this.w = f();
    this.age = f();
    this.size = f();
    this.spin = f();
    this.spinRate = f();
    this.r = f();
    this.g = f();
    this.b = f();
    this.flags = new Uint8Array(capacity);
    this.W = 80;
    this.H = 80;
    this.margin = 10;
    this.maxAge = 16;
    this.spinSeed = 0;
  }

  setField(W, H) {
    this.W = W;
    this.H = H;
  }

  /** Adds a shard; `speed` eases toward `target` at `rate` per second, `turn` bends the heading. */
  spawn(x, y, heading, speed, target, rate, turn, size, color) {
    if (this.count >= this.limit) return -1;
    const i = this.count++;
    this.x[i] = x;
    this.y[i] = y;
    this.h[i] = heading;
    this.cos[i] = Math.cos(heading);
    this.sin[i] = Math.sin(heading);
    this.s[i] = speed;
    this.st[i] = target;
    this.sk[i] = rate;
    this.w[i] = turn;
    this.age[i] = 0;
    this.size[i] = size;
    this.spinSeed = (this.spinSeed + 2.399963) % 6.283185;
    this.spin[i] = this.spinSeed;
    this.spinRate[i] = 3 + ((i * 7919) % 13) * 0.45;
    this.r[i] = color[0];
    this.g[i] = color[1];
    this.b[i] = color[2];
    this.flags[i] = 0;
    return i;
  }

  remove(i) {
    const last = --this.count;
    if (i === last) return;
    this.x[i] = this.x[last];
    this.y[i] = this.y[last];
    this.h[i] = this.h[last];
    this.cos[i] = this.cos[last];
    this.sin[i] = this.sin[last];
    this.s[i] = this.s[last];
    this.st[i] = this.st[last];
    this.sk[i] = this.sk[last];
    this.w[i] = this.w[last];
    this.age[i] = this.age[last];
    this.size[i] = this.size[last];
    this.spin[i] = this.spin[last];
    this.spinRate[i] = this.spinRate[last];
    this.r[i] = this.r[last];
    this.g[i] = this.g[last];
    this.b[i] = this.b[last];
    this.flags[i] = this.flags[last];
  }

  update(dt) {
    const { x, y, h, cos, sin, s, st, sk, w, age, spin, spinRate } = this;
    const xMax = this.W + this.margin;
    const yMax = this.H + this.margin;
    const maxAge = this.maxAge;
    // A step turns a shard by a few thousandths of a radian and eases its speed by a few percent, so the rotation's
    // cosine and sine and the ease's 1 - e^-k come from their first terms: no trig or exp per shard per step.
    for (let i = this.count - 1; i >= 0; i--) {
      if (w[i] !== 0) {
        const a = w[i] * dt;
        const a2 = a * a;
        const ca = 1 - a2 * 0.5 * (1 - a2 / 12);
        const sa = a * (1 - (a2 / 6) * (1 - a2 / 20));
        const c0 = cos[i];
        h[i] += a;
        cos[i] = c0 * ca - sin[i] * sa;
        sin[i] = sin[i] * ca + c0 * sa;
      }
      if (sk[i] > 0) {
        const k = sk[i] * dt;
        s[i] += (st[i] - s[i]) * k * (1 - (k / 2) * (1 - (k / 3) * (1 - k / 4)));
      }
      const v = s[i] * dt;
      x[i] += cos[i] * v;
      y[i] += sin[i] * v;
      age[i] += dt;
      spin[i] += spinRate[i] * dt;
      if (x[i] > xMax || x[i] < -xMax || y[i] > yMax || y[i] < -yMax || age[i] > maxAge) this.remove(i);
    }
  }

  /** Pushes every shard away from (cx, cy), harder the closer it is: the shock of a death. */
  blast(cx, cy, dt, strength) {
    const { x, y } = this;
    for (let i = 0; i < this.count; i++) {
      const dx = x[i] - cx;
      const dy = y[i] - cy;
      const d = Math.sqrt(dx * dx + dy * dy) + 0.001;
      const push = (strength * dt) / (0.35 + d * 0.02);
      x[i] += (dx / d) * push;
      y[i] += (dy / d) * push;
    }
  }

  clear() {
    this.count = 0;
  }
}
