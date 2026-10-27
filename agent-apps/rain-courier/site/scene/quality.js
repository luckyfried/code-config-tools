// The quality tier, picked once and then stepped down if frames run long.
// high: planar reflection, 6,000 streaks, bloom, depth of field, lens drops.
// mid: cube-map street, 3,000 streaks, bloom at half resolution.
// low: cube-map street, 1,500 streaks, no post-processing, half the city blocks.
const TIERS = {
  high: { rain: 6000, reflector: true, post: true, blocks: [9, 9], ratio: 2 },
  mid: { rain: 3000, reflector: false, post: true, blocks: [9, 9], ratio: 2 },
  low: { rain: 1500, reflector: false, post: false, blocks: [7, 6], ratio: 1.5 },
};

export function pickTier() {
  const asked = new URLSearchParams(location.search).get("tier");
  if (asked && TIERS[asked]) return asked;
  const phone = matchMedia("(pointer: coarse)").matches || Math.min(innerWidth, innerHeight) < 768 || innerWidth < 768;
  const weak = (navigator.hardwareConcurrency || 8) <= 2;
  if (weak) return "low";
  return phone ? "mid" : "high";
}

export function tierSettings(tier) {
  return { ...TIERS[tier] };
}

// After the first 120 frames, a mean frame over 20 ms drops one step: ratio 1.5, then 1, then post off.
export function createGovernor(onStep) {
  const STEPS = ["ratio-1.5", "ratio-1", "post-off"];
  let frames = 0;
  let sum = 0;
  let step = 0;
  return {
    sample(ms) {
      frames++;
      if (frames <= 120) return;
      sum += Math.min(ms, 100);
      if (frames % 90 === 0) {
        const mean = sum / 90;
        sum = 0;
        if (mean > 20 && step < STEPS.length) onStep(STEPS[step++]);
      }
    },
  };
}
