// The sounding notes as light: each note is a wave source with a place, a pitch, a color, and an envelope that
// follows its voice's attack, decay, sustain, and release. The field, the scope before sound starts, and the
// ring's flashes all read this list.

export const MAX_SOURCES = 16;

export class Sources {
  constructor() {
    this.list = [];
  }

  /**
   * Starts a source. `x` and `y` are 0 to 1 across and down the window; `look` is the voice's envelope;
   * `strength` scales the whole thing; `length`, when given, releases it by itself after that many seconds.
   */
  add({ id, x, y, freq, color, look, now, strength = 1, length = null }) {
    this.release(id, now);
    const source = { id, x, y, freq, color, look, strength, born: now, releasedAt: null, level: 0, amp: 0, until: null };
    if (length !== null) source.until = now + length;
    if (this.list.length >= MAX_SOURCES) {
      let weakest = 0;
      for (let i = 1; i < this.list.length; i += 1) if (this.list[i].amp < this.list[weakest].amp) weakest = i;
      this.list.splice(weakest, 1);
    }
    this.list.push(source);
    return source;
  }

  release(id, now) {
    for (const source of this.list) {
      if (source.id === id && source.releasedAt === null) {
        source.level = held(source, now);
        source.releasedAt = now;
      }
    }
  }

  releaseAll(now) {
    for (const source of this.list) {
      if (source.releasedAt === null) {
        source.level = held(source, now);
        source.releasedAt = now;
      }
    }
  }

  update(now) {
    for (const source of this.list) {
      if (source.until !== null && source.releasedAt === null && now >= source.until) {
        source.level = held(source, source.until);
        source.releasedAt = source.until;
      }
      if (source.releasedAt === null) {
        source.amp = held(source, now) * source.strength;
      } else {
        const tau = Math.max(0.02, source.look.release / 4.6);
        source.amp = source.level * Math.exp(-(now - source.releasedAt) / tau) * source.strength;
      }
    }
    this.list = this.list.filter((source) => source.releasedAt === null || source.amp > 0.004);
  }

  get count() {
    return this.list.length;
  }
}

/** The envelope's level `now` while the note is held: up over the attack, then down toward the sustain. */
function held(source, now) {
  const { attack, decay, sustain } = source.look;
  const t = Math.max(0, now - source.born);
  if (t < attack) return t / Math.max(attack, 1e-3);
  return sustain + (1 - sustain) * Math.exp(-(t - attack) / Math.max(decay / 3, 1e-3));
}
