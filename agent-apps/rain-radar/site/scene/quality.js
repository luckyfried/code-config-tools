// The quality tier, picked once from the device and stepped down when frames run long.

export function pickTier() {
  const phone = matchMedia("(pointer: coarse)").matches || innerWidth < 768;
  const ratio = Math.min(devicePixelRatio || 1, 2);
  return phone
    ? { name: "phone", phone: true, ratio, particles: 1800, trail: 1024, glow: true }
    : { name: "desktop", phone: false, ratio, particles: 3500, trail: 2048, glow: true };
}

// Watches frame times; after 120 frames a mean over 20 ms takes one step down and the count starts again.
export function createGovernor(tier, apply) {
  const steps = [
    () => tier.ratio > 1.5 && ((tier.ratio = 1.5), true),
    () => tier.ratio > 1 && ((tier.ratio = 1), true),
    () => tier.particles > 900 && ((tier.particles = Math.round(tier.particles / 2)), true),
    () => tier.glow && ((tier.glow = false), true),
  ];
  let count = 0;
  let sum = 0;
  return (ms) => {
    if (ms > 250) return; // a hidden tab or a stall, never a measure of the scene
    count++;
    sum += ms;
    if (count < 120) return;
    const mean = sum / count;
    count = 0;
    sum = 0;
    if (mean <= 20) return;
    for (const step of steps) {
      if (step()) {
        apply(tier);
        return;
      }
    }
  };
}
