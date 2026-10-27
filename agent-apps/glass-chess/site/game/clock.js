// The chess clock: two remaining times, an increment added after each move, and the side whose time runs.
// Times are milliseconds; `now` is passed in so a saved game resumes with the time it had.

export const CLOCKS = {
  none: null,
  "5+0": { base: 5 * 60000, inc: 0 },
  "10+0": { base: 10 * 60000, inc: 0 },
  "15+10": { base: 15 * 60000, inc: 10000 },
};

export class Clock {
  constructor(kind, saved) {
    this.kind = CLOCKS[kind] ? kind : "none";
    const spec = CLOCKS[this.kind];
    this.inc = spec ? spec.inc : 0;
    this.left = saved?.left ? { ...saved.left } : { w: spec ? spec.base : 0, b: spec ? spec.base : 0 };
    this.running = null;
    this.since = 0;
  }

  get enabled() { return this.kind !== "none"; }

  start(side, now) {
    if (!this.enabled) return;
    this.running = side;
    this.since = now;
  }

  // The mover's time stops, the increment lands, and the other side's time starts.
  press(side, now) {
    if (!this.enabled) return;
    if (this.running === side) this.left[side] = Math.max(0, this.left[side] - (now - this.since)) + this.inc;
    this.start(side === "w" ? "b" : "w", now);
  }

  stop(now) {
    if (!this.enabled || !this.running) return;
    this.left[this.running] = Math.max(0, this.left[this.running] - (now - this.since));
    this.running = null;
  }

  remaining(side, now) {
    if (!this.enabled) return null;
    const base = this.left[side];
    return this.running === side ? Math.max(0, base - (now - this.since)) : base;
  }

  flagged(now) {
    if (!this.enabled || !this.running) return null;
    return this.remaining(this.running, now) <= 0 ? this.running : null;
  }

  save(now) {
    return { left: { w: this.remaining("w", now), b: this.remaining("b", now) } };
  }
}

export function formatClock(ms) {
  if (ms === null) return "";
  const total = Math.ceil(ms / 1000);
  const m = Math.floor(total / 60), s = total % 60;
  if (ms < 10000) return `0:${(ms / 1000).toFixed(1).padStart(4, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}
