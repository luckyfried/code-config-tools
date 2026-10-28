// The quality tier, picked once and adapted: "phone" on a coarse pointer or a narrow screen, "desktop" otherwise.
export function pickTier() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  return coarse || innerWidth < 768 ? "phone" : "desktop";
}

export function tierSettings(tier) {
  if (tier === "phone") {
    return { tier, pixelRatio: Math.min(devicePixelRatio || 1, 2), shadows: false, motes: 160, lamps: false, atlas: 1024 };
  }
  return { tier, pixelRatio: Math.min(devicePixelRatio || 1, 2), shadows: true, motes: 360, lamps: true, atlas: 1024 };
}

export function canWebGL() {
  try {
    const c = document.createElement("canvas");
    return Boolean(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

/** A phone too small to hold a 3D shelf at speed gets the flat shelf. */
export function weakDevice() {
  const memory = navigator.deviceMemory;
  const cores = navigator.hardwareConcurrency;
  return (memory !== undefined && memory <= 1) || (cores !== undefined && cores <= 2);
}

/**
 * Watches frame times and steps quality down once when the mean over a window runs past 20 ms:
 * pixel ratio 1.5, then 1, then shadows off.
 */
export function createGovernor(onStep) {
  let frames = 0;
  let total = 0;
  let level = 0;
  let skip = 120;
  return (dt) => {
    if (skip > 0) {
      skip -= 1;
      return;
    }
    frames += 1;
    total += dt;
    if (frames < 90) return;
    const mean = (total / frames) * 1000;
    frames = 0;
    total = 0;
    if (mean > 20 && level < 3) {
      level += 1;
      onStep(level);
      skip = 60;
    }
  };
}
