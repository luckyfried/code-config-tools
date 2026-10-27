// One drill: the expected characters, what was typed against them, and the numbers a result is made of.
// A wrong character holds the caret where it is until the right one comes, and counts against the expected key.

import { matches, statName } from "./layout.js";

export class Drill {
  constructor({ text, layout, mode, seconds, handlers }) {
    this.chars = Array.from(text);
    this.layout = layout;
    this.mode = mode;
    this.seconds = seconds;
    this.on = handlers || {};
    this.i = 0;
    this.startedAt = 0;
    this.lastAt = 0;
    this.endedAt = 0;
    this.keystrokes = 0;
    this.correct = 0;
    this.attempted = new Set();
    this.missed = new Set();
    this.stats = new Map();
    this.errorsHere = new Map();
  }

  get started() {
    return this.startedAt > 0;
  }

  get finished() {
    return this.endedAt > 0;
  }

  get expected() {
    return this.chars[this.i];
  }

  stat(name) {
    if (!this.stats.has(name)) this.stats.set(name, { samples: 0, errors: 0, time: 0, timed: 0 });
    return this.stats.get(name);
  }

  type(ch, now = performance.now()) {
    if (this.finished || this.i >= this.chars.length) return;
    if (!this.started) {
      this.startedAt = now;
      this.lastAt = now;
      this.on.start?.();
    }
    const expected = this.chars[this.i];
    const name = statName(this.layout, expected);
    const s = this.stat(name);
    const first = !this.attempted.has(this.i);
    this.attempted.add(this.i);
    this.keystrokes += 1;
    if (matches(this.layout, ch, expected)) {
      if (first) s.samples += 1;
      if (this.i > 0) {
        s.time += now - this.lastAt;
        s.timed += 1;
      }
      this.lastAt = now;
      this.correct += 1;
      const index = this.i;
      this.i += 1;
      this.on.advance?.(index, this.missed.has(index), ch);
      if (this.i >= this.chars.length) this.finish(now);
    } else {
      if (first) {
        s.samples += 1;
        s.errors += 1;
      }
      this.missed.add(this.i);
      this.on.wrong?.(this.i, ch, expected);
    }
  }

  elapsed(now = performance.now()) {
    if (!this.started) return 0;
    return ((this.finished ? this.endedAt : now) - this.startedAt) / 1000;
  }

  wpm(now) {
    const seconds = Math.max(1, this.elapsed(now));
    return this.i / 5 / (seconds / 60);
  }

  accuracy() {
    return this.keystrokes ? this.correct / this.keystrokes : 1;
  }

  finish(now = performance.now()) {
    if (this.finished || !this.started) return;
    this.endedAt = Math.min(now, this.startedAt + this.seconds * 1000);
    this.on.finish?.();
  }

  /** The drill as a history row, plus the slowest and most-missed keys for the results card. */
  result({ input, date = new Date() }) {
    const errorsByKey = {};
    const samplesByKey = {};
    const slow = [];
    const missed = [];
    for (const [name, s] of this.stats) {
      if (s.samples) samplesByKey[name] = s.samples;
      if (s.errors) {
        errorsByKey[name] = s.errors;
        missed.push({ name, errors: s.errors, samples: s.samples });
      }
      if (s.timed >= 2 && name !== "enter") slow.push({ name, ms: s.time / s.timed });
    }
    slow.sort((a, b) => b.ms - a.ms);
    missed.sort((a, b) => b.errors - a.errors || b.errors / b.samples - a.errors / a.samples);
    return {
      row: {
        date: date.toISOString(),
        mode: this.mode,
        layout: this.layout.id,
        input,
        seconds: Math.round(this.elapsed() * 10) / 10,
        wpm: Math.round(this.wpm() * 10) / 10,
        accuracy: Math.round(this.accuracy() * 1000) / 1000,
        chars: this.i,
        errorsByKey,
        samplesByKey,
      },
      slow: slow.slice(0, 3),
      missed: missed.slice(0, 3),
    };
  }
}
