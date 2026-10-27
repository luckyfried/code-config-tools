// The numbers behind the chart: days as integers, the exponential moving average, the seven-day change, the goal
// projection, and the made-up months of weigh-ins a first visit shows when the inputs ask for them.

const DAY_MS = 86400000;

export const LB_PER_KG = 2.20462262;

// A step on the scale is a tenth of a unit; "holding" is a week's change under one step's worth, per unit.
export const HOLD_KG_PER_WEEK = 0.1;

export function dayOf(iso) {
  const [y, m, d] = iso.split("-").map(Number);
  return Math.round(Date.UTC(y, m - 1, d) / DAY_MS);
}

export function isoOf(day) {
  return new Date(day * DAY_MS).toISOString().slice(0, 10);
}

export function todayDay(now = new Date()) {
  return Math.round(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / DAY_MS);
}

export function dateOfDay(day) {
  const d = new Date(day * DAY_MS);
  return new Date(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
}

// Entries in, sorted points out: { day, date, value, note, trend } with values in kilograms.
export function withTrend(entries, smoothing) {
  const sorted = [...entries].sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
  let trend = null;
  return sorted.map((e) => {
    trend = trend === null ? e.value : trend + smoothing * (e.value - trend);
    return { day: dayOf(e.date), date: e.date, value: e.value, note: e.note || "", trend };
  });
}

function trendAt(points, day) {
  if (!points.length || day <= points[0].day) return points.length ? points[0].trend : null;
  for (let i = points.length - 1; i >= 0; i -= 1) {
    if (points[i].day <= day) {
      const a = points[i];
      const b = points[i + 1];
      if (!b) return a.trend;
      return a.trend + ((b.trend - a.trend) * (day - a.day)) / (b.day - a.day);
    }
  }
  return points[0].trend;
}

// The trend's change over the seven days before its last point, in kilograms; null until two weigh-ins exist.
export function weekDelta(points) {
  if (points.length < 2) return null;
  const last = points[points.length - 1];
  const span = Math.min(7, last.day - points[0].day);
  if (span <= 0) return null;
  return ((last.trend - trendAt(points, last.day - span)) * 7) / span;
}

// Where the trend meets the goal at the current seven-day rate.
// state: "empty" | "reached" | "holding" | "toward" (with day) | "away"
export function projection(points, goalKg) {
  if (!points.length) return { state: "empty" };
  const last = points[points.length - 1];
  const gap = goalKg - last.trend;
  if (Math.abs(gap) < 0.05) return { state: "reached", trend: last.trend };
  const week = weekDelta(points);
  if (week === null || Math.abs(week) < HOLD_KG_PER_WEEK) return { state: "holding", trend: last.trend, week };
  if (Math.sign(week) !== Math.sign(gap)) return { state: "away", trend: last.trend, week };
  const days = gap / (week / 7);
  return { state: "toward", trend: last.trend, week, day: last.day + days, fromDay: last.day };
}

function mulberry32(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const SAMPLE_NOTES = {
  9: "Pizza night",
  23: "Long run yesterday",
  38: "Travel day",
  51: "Slept badly",
  64: "Started walking at lunch",
  80: "Salty dinner out",
};

// Ninety-six days that end yesterday, drifting down toward the goal with a plateau in the middle and the day-to-day
// noise of a real bathroom scale. The same goal always gives the same months.
export function sampleEntries(goalKg, today = todayDay()) {
  const rand = mulberry32(20261022);
  const gauss = () => (rand() + rand() + rand() + rand() - 2) * 0.62;
  const out = [];
  let base = goalKg + 8.1;
  const first = today - 96;
  for (let i = 0; i < 96; i += 1) {
    const day = first + i;
    base += i < 34 ? -0.07 : i < 48 ? -0.004 : -0.082;
    if (rand() < 0.08 && i > 2 && i < 93) continue;
    const weekday = dateOfDay(day).getDay();
    const weekend = weekday === 1 ? 0.35 : weekday === 0 ? 0.2 : 0;
    const value = Math.round((base + weekend + gauss() * 0.75) * 10) / 10;
    out.push({ date: isoOf(day), value, note: SAMPLE_NOTES[i] || "" });
  }
  return out;
}
