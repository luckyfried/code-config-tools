// The quality tier: how finely the field is drawn. Phones draw it at half the window's CSS pixels, desktops at
// two thirds; the waves are soft, so the GPU's own smoothing fills the rest. After the first 120 frames, a mean
// frame time over 20 ms steps the field down, and again if it stays slow.

export function pickTier() {
  const coarse = window.matchMedia("(pointer: coarse)").matches;
  return coarse || window.innerWidth < 768 ? "phone" : "desktop";
}

export const TIERS = {
  phone: { scale: 0.5, trail: 0.25 },
  desktop: { scale: 0.66, trail: 0.3 },
};

export class Adapt {
  constructor(tier) {
    this.scale = TIERS[tier].scale;
    this.trail = TIERS[tier].trail;
    this.frames = 0;
    this.total = 0;
  }

  /** Counts one frame; answers true when the field should be redrawn smaller. */
  frame(ms) {
    if (ms > 250) return false;
    this.frames += 1;
    this.total += ms;
    if (this.frames < 120) return false;
    const mean = this.total / this.frames;
    this.frames = 0;
    this.total = 0;
    if (mean > 20 && this.scale > 0.3) {
      this.scale = Math.max(0.3, this.scale * 0.75);
      return true;
    }
    return false;
  }
}
