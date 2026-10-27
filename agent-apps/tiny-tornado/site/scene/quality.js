// Quality tiers. High: 3,000 debris chips, the full grass patch, rain, and bloom at full resolution. Mid: 1,500
// chips, a third of the grass, bloom at half resolution. Low: 600 chips, no grass blades, no rain, and no post.
// A phone starts at mid; the adaptive ladder then steps down one rung at a time while frames run over budget, and
// never steps back up during a visit.

export const TIERS = {
  high: { name: "high", ratio: 2, chips: 3000, blades: 36000, rain: 2200, post: true, bloomScale: 1, shadowSize: 2048 },
  mid: { name: "mid", ratio: 1.5, chips: 1500, blades: 12000, rain: 1100, post: true, bloomScale: 0.5, shadowSize: 1024 },
  low: { name: "low", ratio: 1, chips: 600, blades: 0, rain: 0, post: false, bloomScale: 0.5, shadowSize: 0 },
};

export function pickTier() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  return coarse || Math.min(innerWidth, innerHeight) < 600 ? "mid" : "high";
}

export function tierSettings(name) {
  const base = TIERS[name];
  return { ...base, ratio: Math.min(window.devicePixelRatio || 1, base.ratio) };
}

// The first three seconds (shader compiles, the first shadow map) are never measured, and a rung is taken only after
// two slow windows of a second in a row, so one hitch never costs the storm its looks.
export function createAdaptive(settings, apply) {
  const rungs = [];
  if (settings.ratio > 1.5) rungs.push({ ratio: 1.5 });
  if (settings.name === "high") rungs.push({ ...TIERS.mid, ratio: Math.min(settings.ratio, 1.5) });
  if (settings.ratio > 1) rungs.push({ ratio: 1 });
  rungs.push({ ...TIERS.low });
  rungs.push({ ratio: 0.75 });
  const current = { ...settings };
  let samples = 0;
  let total = 0;
  let warm = 3000;
  let slow = 0;
  let rung = 0;
  return {
    current,
    frame(ms) {
      if (warm > 0) {
        warm -= Math.min(ms, 250);
        return;
      }
      samples++;
      total += Math.min(ms, 250);
      if (samples < 60) return;
      const mean = total / samples;
      samples = 0;
      total = 0;
      slow = mean > 20 ? slow + 1 : 0;
      if (slow >= 2 && rung < rungs.length) {
        Object.assign(current, rungs[rung++]);
        apply(current);
        slow = 0;
        warm = 1000;
      }
    },
  };
}
