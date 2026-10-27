// Quality tiers, picked once and stepped down if frames run long. High: refracting glass marble, bloom and radial
// blur, 2048 shadows. Mid (phones): clear glass without refraction over the same swirl and environment, no radial
// blur, 1024 shadows. Low: no post-processing, no shadows, a flat-shaded track.
export const TIERS = {
  high: {
    name: "high",
    pixelRatio: 2,
    post: true,
    radialBlur: true,
    shadows: true,
    shadowSize: 2048,
    transmission: true,
    flat: false,
    particles: 1,
    segments: 64,
    terrainStep: 2,
    trackStep: 1,
  },
  mid: {
    name: "mid",
    pixelRatio: 2,
    post: false,
    radialBlur: false,
    shadows: true,
    shadowSize: 1024,
    transmission: false,
    flat: false,
    particles: 0.5,
    segments: 40,
    terrainStep: 4,
    trackStep: 1.5,
  },
  low: {
    name: "low",
    pixelRatio: 1,
    post: false,
    radialBlur: false,
    shadows: false,
    shadowSize: 512,
    transmission: false,
    flat: true,
    particles: 0.5,
    segments: 24,
    terrainStep: 8,
    trackStep: 2,
  },
};

export function pickTier() {
  const asked = new URLSearchParams(location.search).get("tier");
  if (asked && TIERS[asked]) return { ...TIERS[asked] };
  const coarse = matchMedia("(pointer: coarse)").matches;
  const narrow = innerWidth < 768;
  return { ...(coarse || narrow ? TIERS.mid : TIERS.high) };
}

// Watches frame times; after the first 120 frames, a mean over 20 ms asks for one step down.
export class FrameWatch {
  constructor(onSlow) {
    this.onSlow = onSlow;
    this.times = [];
    this.skip = 30;
    this.steps = 0;
  }

  push(ms) {
    if (this.skip > 0) {
      this.skip -= 1;
      return;
    }
    this.times.push(ms);
    if (this.times.length < 120) return;
    const mean = this.times.reduce((a, b) => a + b, 0) / this.times.length;
    this.times.length = 0;
    if (mean > 20 && this.steps < 4) {
      this.steps += 1;
      this.skip = 30;
      this.onSlow(this.steps);
    }
  }
}
