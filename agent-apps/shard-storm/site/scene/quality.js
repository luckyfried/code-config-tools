// Quality tiers. A phone starts at mid and a desktop at high, a tier lower for each step the page's own warm-up ran
// slow; then the frames are timed from the first second and a device that misses its frames steps down until it holds
// 60 Hz. Below high every tier keeps one pixel ratio and one bloom size, so a step never reallocates the canvas or a
// render target and never costs a frame: it only lowers the shard cap, how often the HUD rewrites its numbers, and,
// on the floor, the bloom.
export const TIERS = {
  high: { name: "high", bullets: 8192, post: true, bloomScale: 1, dpr: 2, hudEvery: 1 },
  mid: { name: "mid", bullets: 4096, post: true, bloomScale: 0.5, dpr: 1.5, hudEvery: 2 },
  low: { name: "low", bullets: 2560, post: true, bloomScale: 0.5, dpr: 1.5, hudEvery: 3 },
  floor: { name: "floor", bullets: 2048, post: false, bloomScale: 0.5, dpr: 1.5, hudEvery: 4 },
};

const ORDER = ["high", "mid", "low", "floor"];

// The warm-up simulates seven seconds of the demo run before the first frame. A phone that does it in under
// SLOW_WARM_MS keeps its tier; each further SLOW_WARM_MS past that starts it one tier lower.
const SLOW_WARM_MS = 150;

const lower = (tier, steps) => TIERS[ORDER[Math.min(ORDER.length - 1, ORDER.indexOf(tier.name) + steps)]];

/** The tier to build the scene at, before anything has been timed. */
export function firstTier() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  return coarse || Math.min(innerWidth, innerHeight) < 600 ? TIERS.mid : TIERS.high;
}

/** The tier to open at once the warm-up has run in `warmMs`. */
export function warmedTier(tier, warmMs) {
  return lower(tier, Math.max(0, Math.floor(warmMs / SLOW_WARM_MS)));
}

/**
 * Counts slow frames (over 20 ms, a missed 60 Hz tick) in windows of 30 after a few frames of settling; a window
 * with more than three steps down a tier and calls onStep(nextTier). It keeps watching, so a later, heavier wave
 * steps down too.
 */
export function createProbe(start, onStep) {
  let tier = start;
  let skip = 4;
  let frames = 0;
  let slow = 0;
  return {
    get tier() {
      return tier;
    },
    sample(ms) {
      if (tier.name === ORDER[ORDER.length - 1]) return;
      if (skip > 0) {
        skip--;
        return;
      }
      frames++;
      if (ms > 20) slow++;
      if (frames < 30) return;
      const missed = slow > 3;
      frames = 0;
      slow = 0;
      if (!missed) return;
      tier = lower(tier, 1);
      skip = 4;
      onStep(tier);
    },
  };
}
