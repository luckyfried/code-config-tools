// Picks the quality tier once, then steps it down when frames run long.
// high: depth of field, full shimmer, bloom, lens flare, 2048 shadows (desktop).
// mid: no depth of field or bloom, at the phone's own pixel ratio, 2048 soft shadows (phones).
// low: no post-processing and no lens flare.
// Every tier renders the scene multisampled (the post stack's targets carry the samples), so edges stay smooth.

const TIERS = {
  high: { name: "high", ratio: 2, samples: 4, post: true, dof: true, bloom: true, postScale: 1, flare: true, shadowSize: 2048, particles: 1 },
  mid: { name: "mid", ratio: 3, samples: 4, post: true, dof: false, bloom: false, postScale: 0.5, flare: true, shadowSize: 2048, particles: 0.5 },
  low: { name: "low", ratio: 1, post: false, dof: false, bloom: false, postScale: 0.5, flare: false, shadowSize: 1024, particles: 0.4 },
};

export function pickTier() {
  const params = new URLSearchParams(location.search);
  const forced = params.get("tier");
  if (forced && TIERS[forced]) return { ...TIERS[forced] };
  const coarse = matchMedia("(pointer: coarse)").matches;
  const narrow = Math.min(innerWidth, innerHeight) < 768 && Math.max(innerWidth, innerHeight) < 1100;
  return { ...(coarse || narrow ? TIERS.mid : TIERS.high) };
}

/** Watches frame times; after the first 120 frames, a mean over 20 ms steps down once per window. */
export class FrameGovernor {
  constructor(onStep) {
    this.onStep = onStep;
    this.frames = 0;
    this.sum = 0;
    this.count = 0;
    this.steps = 0;
  }

  sample(ms) {
    this.frames += 1;
    if (this.frames < 120 || document.hidden) return;
    this.sum += Math.min(ms, 100);
    this.count += 1;
    if (this.count < 90) return;
    const mean = this.sum / this.count;
    this.sum = 0;
    this.count = 0;
    if (mean > 20 && this.steps < 3) {
      this.steps += 1;
      this.onStep(this.steps);
    }
  }
}
