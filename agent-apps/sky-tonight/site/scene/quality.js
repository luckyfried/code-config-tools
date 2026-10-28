// Quality tier, picked once and stepped down when frames run long: a phone that cannot hold 60 fps gets device
// pixel ratio 1, stars to magnitude 5, and no Milky Way texture.

export function pickTier() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  const small = Math.min(innerWidth, innerHeight) < 768 || innerWidth < 768;
  const phone = coarse || small;
  return {
    name: phone ? "phone" : "desktop",
    phone,
    pixelRatio: Math.min(devicePixelRatio || 1, 2),
    magCut: 6.5,
    milkyWay: true,
    silhouette: phone ? [4096, 256] : [8192, 512],
  };
}

// Watches frame times; after the first 120 frames, a mean over 20 ms takes one step down.
export function createGovernor(tier, onStep) {
  const times = [];
  let frames = 0;
  let step = 0;
  return {
    sample(ms) {
      frames += 1;
      if (frames < 120) return;
      times.push(ms);
      if (times.length < 90) return;
      const mean = times.reduce((s, x) => s + x, 0) / times.length;
      times.length = 0;
      if (mean <= 20 || step >= 2) return;
      step += 1;
      if (step === 1) {
        tier.pixelRatio = 1;
        tier.magCut = 5;
        tier.milkyWay = false;
      } else {
        tier.pixelRatio = 0.75;
      }
      onStep(tier);
    },
  };
}
