// Picks the quality tier once, then steps down if the frames run long: pixel ratio 2, then 1.5, then 1, then the
// bloom pass off (merges still flash through the cube's own glow). A phone draws without the bloom pass from the
// start: its glow is the halos, pools, and bursts, which are drawn in the scene itself.
export function pickTier() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  return coarse || innerWidth < 768 ? "phone" : "desktop";
}

export const TIERS = {
  phone: { ratio: 2, bloom: false, bloomScale: 0.5 },
  desktop: { ratio: 2, bloom: true, bloomScale: 0.5 },
};

export function createGovernor({ onStep }) {
  const steps = [2, 1.5, 1, "no-bloom"];
  let at = 0;
  let frames = 0;
  let total = 0;
  return {
    sample(ms) {
      if (document.hidden || ms > 250) return;
      frames += 1;
      if (frames <= 30) return;
      total += ms;
      if (frames < 150) return;
      const mean = total / (frames - 30);
      frames = 0;
      total = 0;
      if (mean > 20 && at < steps.length - 1) {
        at += 1;
        onStep(steps[at]);
      }
    },
  };
}
