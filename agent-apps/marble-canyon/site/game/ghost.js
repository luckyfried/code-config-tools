// The ghost: the best run sampled every 50 ms (s along the track, u across it, height above it, speed), kept in
// this browser's localStorage under the seed and length, and replayed by interpolation.

export const GHOST_INTERVAL = 0.05;
const FIELDS = 4;
const PREFIX = "marble-canyon:";

export class GhostRecorder {
  constructor() {
    this.samples = [];
    this.next = 0;
  }

  reset() {
    this.samples.length = 0;
    this.next = 0;
  }

  record(time, s, u, h, v) {
    while (time >= this.next) {
      this.samples.push(s, u, h, v);
      this.next += GHOST_INTERVAL;
    }
  }

  finish() {
    return Float32Array.from(this.samples);
  }
}

export class GhostPlayer {
  constructor(samples) {
    this.samples = samples;
    this.count = samples.length / FIELDS;
    this.out = { s: 0, u: 0, h: 0, v: 0, done: false };
  }

  at(time) {
    const f = time / GHOST_INTERVAL;
    const i = Math.min(this.count - 1, Math.floor(f));
    const j = Math.min(this.count - 1, i + 1);
    const k = Math.min(1, f - i);
    const d = this.samples;
    const a = i * FIELDS;
    const b = j * FIELDS;
    const out = this.out;
    out.s = d[a] + (d[b] - d[a]) * k;
    out.u = d[a + 1] + (d[b + 1] - d[a + 1]) * k;
    out.h = d[a + 2] + (d[b + 2] - d[a + 2]) * k;
    out.v = d[a + 3] + (d[b + 3] - d[a + 3]) * k;
    out.done = f >= this.count - 1;
    return out;
  }

  // Ghost time at which it passed arc length s, for the live delta.
  timeAt(s) {
    const d = this.samples;
    let lo = 0;
    let hi = this.count - 1;
    if (s <= d[0]) return 0;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (d[mid * FIELDS] < s) lo = mid;
      else hi = mid;
    }
    const s0 = d[lo * FIELDS];
    const s1 = d[hi * FIELDS];
    const k = s1 > s0 ? (s - s0) / (s1 - s0) : 0;
    return (lo + Math.max(0, Math.min(1, k))) * GHOST_INTERVAL;
  }
}

const encode = (floats) => {
  const bytes = new Uint8Array(floats.buffer, floats.byteOffset, floats.byteLength);
  let text = "";
  for (let i = 0; i < bytes.length; i += 0x8000) text += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(text);
};

const decode = (text) => {
  const raw = atob(text);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) bytes[i] = raw.charCodeAt(i);
  return new Float32Array(bytes.buffer);
};

const keyFor = (seed, lengthName) => `${PREFIX}best:${seed.toLowerCase()}:${lengthName}`;

export function loadBest(seed, lengthName) {
  try {
    const raw = localStorage.getItem(keyFor(seed, lengthName));
    if (!raw) return null;
    const data = JSON.parse(raw);
    if (typeof data.time !== "number" || typeof data.ghost !== "string") return null;
    return { time: data.time, splits: data.splits ?? [], name: data.name ?? "", ghost: decode(data.ghost) };
  } catch {
    return null;
  }
}

export function saveBest(seed, lengthName, best) {
  try {
    const data = { time: best.time, splits: best.splits, name: best.name, ghost: encode(best.ghost) };
    localStorage.setItem(keyFor(seed, lengthName), JSON.stringify(data));
    return true;
  } catch {
    return false;
  }
}

export function loadSetting(name, fallback) {
  try {
    const raw = localStorage.getItem(`${PREFIX}${name}`);
    return raw === null ? fallback : JSON.parse(raw);
  } catch {
    return fallback;
  }
}

export function saveSetting(name, value) {
  try {
    localStorage.setItem(`${PREFIX}${name}`, JSON.stringify(value));
  } catch {
    // Private browsing without storage: the setting lasts this visit only.
  }
}
