// Quality tiers. High is the desktop look; mid keeps bloom and the tint pass; low is the tint pass alone.
// The tier is picked once, then a governor steps down when the mean frame runs long.

export const TIERS = {
  high: {
    name: "high", pixelRatio: 2, bloom: true, godRays: true, bokeh: true, caustics: true, fish: 400, snow: 7000,
    trenchSegments: 84, ringStep: 2.2, msaa: 4,
  },
  mid: {
    name: "mid", pixelRatio: 1.5, bloom: true, godRays: false, bokeh: false, caustics: true, fish: 200, snow: 3200,
    trenchSegments: 64, ringStep: 2.8, msaa: 0,
  },
  low: {
    name: "low", pixelRatio: 1, bloom: false, godRays: false, bokeh: false, caustics: false, fish: 100, snow: 1600,
    trenchSegments: 52, ringStep: 3.4, msaa: 0,
  },
};

export function pickTier() {
  const asked = new URLSearchParams(location.search).get("tier");
  if (asked && TIERS[asked]) return { ...TIERS[asked] };
  const coarse = matchMedia("(pointer: coarse)").matches;
  return { ...(coarse || innerWidth < 768 ? TIERS.mid : TIERS.high) };
}

/**
 * Watches frame times. After the first 120 frames, and again every 120 frames after a step, a mean frame over
 * 20 ms calls onStep with the next lighter setting: a lower pixel ratio first, then fewer passes.
 */
export function createGovernor(tier, onStep) {
  const steps = [];
  if (tier.pixelRatio > 1.5) steps.push({ pixelRatio: 1.5 });
  if (tier.pixelRatio > 1) steps.push({ pixelRatio: 1 });
  if (tier.bokeh || tier.godRays) steps.push({ bokeh: false, godRays: false });
  if (tier.bloom) steps.push({ bloom: false });
  let frames = 0;
  let total = 0;
  let skip = 20;
  return {
    sample(ms) {
      if (skip > 0) {
        skip--;
        return;
      }
      if (ms > 250) return;
      frames++;
      total += ms;
      if (frames < 120) return;
      const mean = total / frames;
      frames = 0;
      total = 0;
      if (mean > 20 && steps.length) {
        const step = steps.shift();
        Object.assign(tier, step);
        onStep(step);
        skip = 30;
      }
    },
  };
}
