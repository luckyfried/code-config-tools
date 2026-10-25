// Quality tiers. The tier is picked once from the device, then the adaptive ladder steps down one rung at a time
// while the measured frame time stays over budget. Rungs only ever go down during a visit.

export function pickTier() {
  const coarse = matchMedia("(pointer: coarse)").matches;
  return coarse || innerWidth < 768 ? "phone" : "desktop";
}

export const TIERS = {
  desktop: { ratio: 2, antialias: true, shadowSize: 2048, post: true, bloomScale: 1, flora: 1, detail: 34, seaDetail: 22, stars: 1600 },
  phone: { ratio: 2, antialias: false, shadowSize: 1024, post: true, bloomScale: 0.5, flora: 0.5, detail: 24, seaDetail: 16, stars: 900 },
};

export function tierSettings(tier) {
  const base = TIERS[tier];
  const dpr = window.devicePixelRatio || 1;
  return { ...base, tier, ratio: Math.min(dpr, base.ratio), antialias: base.antialias || dpr < 2 };
}

// Rungs below the starting tier: mid (1024 shadows, half the flora, bloom at half resolution) and low (no shadows,
// no bloom, a quarter of the flora), with pixel-ratio steps between them. The first three seconds (shader compiles,
// the first shadow map) are never measured, and a rung is taken only after two slow windows in a row, so one hitch
// never costs the planet its looks.
export function createAdaptive(settings, apply) {
  const rungs = [];
  if (settings.ratio > 1.5) rungs.push({ ratio: 1.5 });
  if (settings.ratio > 1) rungs.push({ ratio: 1 });
  if (settings.shadowSize > 1024 || settings.flora > 0.5 || (settings.post && settings.bloomScale > 0.5)) {
    rungs.push({ shadowSize: 1024, flora: 0.5, bloomScale: 0.5 });
  }
  rungs.push({ shadowSize: 0, flora: 0.25, post: false });
  rungs.push({ ratio: Math.min(settings.ratio, 0.75) });

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
