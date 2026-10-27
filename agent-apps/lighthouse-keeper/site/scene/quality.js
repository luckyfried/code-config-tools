// Picks the render tier once and steps it down when the frame time says the device cannot keep up.
export const TIERS = {
  high: { name: "high", pixelRatio: 2, post: true, godRays: true, shadow: 2048, fogLayers: 3, seaSegments: 220, spray: 280, rain: 1, antialias: true, fogSprites: 150 },
  mid: { name: "mid", pixelRatio: 2, post: true, godRays: false, shadow: 1024, fogLayers: 1, seaSegments: 192, spray: 150, rain: 0.6, antialias: true, fogSprites: 70 },
  low: { name: "low", pixelRatio: 1, post: false, godRays: false, shadow: 0, fogLayers: 1, seaSegments: 64, spray: 80, rain: 0.4, antialias: true, fogSprites: 50 },
};

export function pickTier() {
  const asked = new URLSearchParams(location.search).get("tier");
  if (asked && TIERS[asked]) return TIERS[asked];
  const coarse = matchMedia("(pointer: coarse)").matches;
  return coarse || innerWidth < 768 ? TIERS.mid : TIERS.high;
}

export const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");

// After 120 frames, a mean frame time over 20 ms takes one step: a lower pixel ratio, then no post-processing.
export function createGovernor(onStep) {
  let frames = 0;
  let total = 0;
  let steps = 0;
  return (ms) => {
    if (steps >= 3 || document.hidden) return;
    frames += 1;
    total += Math.min(ms, 100);
    if (frames < 120) return;
    const mean = total / frames;
    frames = 0;
    total = 0;
    if (mean > 20) {
      steps += 1;
      onStep(steps);
    }
  };
}
