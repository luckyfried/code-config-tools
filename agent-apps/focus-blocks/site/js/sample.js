// A made-up week for a first visit when the inputs ask for it: six earlier days of blocks, two this morning, and
// a block in its last seconds, so the page opens on the ring burning ember, sees it finish and bloom, and watches
// the next block, at the first length, start cool and full.
import { HOUR, MINUTE, addDays, startOfDay, windowOf } from "./time.js";

// How much of the sample's block is left when the page opens.
const LAST_MS = 6500;

function seeded(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function sampleState(cfg, now) {
  const lengths = cfg.blockLengths;
  const labels = cfg.labels.length ? cfg.labels : [""];
  const pickOf = (r, list) => list[Math.floor(r() * list.length) % list.length];
  const today0 = startOfDay(now);
  const blocks = [];

  for (let d = 6; d >= 1; d--) {
    const day0 = addDays(today0, -d);
    const r = seeded(Math.floor(day0 / HOUR));
    const { from, to } = windowOf(day0, cfg);
    let t = from + (1.5 + r() * 2) * HOUR;
    const count = 2 + Math.floor(r() * 4);
    for (let i = 0; i < count; i++) {
      const end = t + pickOf(r, lengths) * MINUTE;
      if (end > to - HOUR) break;
      blocks.push({ start: Math.round(t / MINUTE) * MINUTE, end: Math.round(end / MINUTE) * MINUTE, label: pickOf(r, labels) });
      t = end + (25 + r() * 110) * MINUTE;
    }
  }

  const next = { minutes: lengths[0], label: labels[1 % labels.length] };
  const runMs = (lengths[1] ?? lengths[0]) * MINUTE;
  const runStart = now - runMs + LAST_MS;
  const { from } = windowOf(today0, cfg);
  let t = runStart - 18 * MINUTE;
  const morning = [];
  for (let i = 0; i < 2; i++) {
    const start = t - lengths[i % lengths.length] * MINUTE;
    if (start < from) break;
    morning.unshift({ start: Math.round(start / MINUTE) * MINUTE, end: Math.round(t / MINUTE) * MINUTE, label: labels[(i + 1) % labels.length] });
    t = start - 22 * MINUTE;
  }
  blocks.push(...morning);

  return {
    blocks,
    active: { start: runStart, ms: runMs, label: labels[0], pausedAt: null, pausedMs: 0, next },
    pick: { ...next },
  };
}
