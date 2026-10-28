// Clock and calendar in the place's own time zone, through Intl alone.

const partsCache = new Map();

function partsFormatter(tz) {
  if (!partsCache.has(tz)) {
    partsCache.set(tz, new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      hourCycle: "h23",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }));
  }
  return partsCache.get(tz);
}

export function validZone(tz) {
  try {
    partsFormatter(tz).format(0);
    return true;
  } catch {
    return false;
  }
}

// The wall clock of `ms` in `tz`, as numbers.
export function wallClock(ms, tz) {
  const out = {};
  for (const p of partsFormatter(tz).formatToParts(new Date(ms))) {
    if (p.type !== "literal") out[p.type] = parseInt(p.value, 10);
  }
  return { year: out.year, month: out.month, day: out.day, hour: out.hour % 24, minute: out.minute, second: out.second };
}

export function offsetMs(ms, tz) {
  const w = wallClock(ms, tz);
  const asUtc = Date.UTC(w.year, w.month - 1, w.day, w.hour, w.minute, w.second);
  return asUtc - Math.floor(ms / 1000) * 1000;
}

// UTC milliseconds of a wall-clock time in `tz`.
export function zonedToUtc(year, month, day, hour, minute, tz) {
  const guess = Date.UTC(year, month - 1, day, hour, minute);
  let ms = guess - offsetMs(guess, tz);
  ms = guess - offsetMs(ms, tz);
  return ms;
}

export function parseLocal(text, tz) {
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(text || "");
  if (!m) return null;
  return zonedToUtc(+m[1], +m[2], +m[3], +m[4], +m[5], tz);
}

const fmtCache = new Map();
function fmt(tz, options) {
  const key = tz + JSON.stringify(options);
  if (!fmtCache.has(key)) fmtCache.set(key, new Intl.DateTimeFormat("en-US", { timeZone: tz, ...options }));
  return fmtCache.get(key);
}

export function formatTime(ms, tz) {
  return fmt(tz, { hour: "numeric", minute: "2-digit" }).format(new Date(ms)).replace(" AM", " am").replace(" PM", " pm");
}

export function formatHour(ms, tz) {
  return fmt(tz, { hour: "numeric" }).format(new Date(ms)).replace(" AM", " am").replace(" PM", " pm");
}

export function formatDay(ms, tz) {
  return fmt(tz, { weekday: "long", month: "long", day: "numeric" }).format(new Date(ms));
}

export function formatShortDay(ms, tz) {
  return fmt(tz, { weekday: "short", month: "short", day: "numeric" }).format(new Date(ms));
}

export function formatYear(ms, tz) {
  return fmt(tz, { year: "numeric" }).format(new Date(ms));
}

// Local noon that starts the night containing `ms` (the night of the evening before when it is past midnight).
export function nightStart(ms, tz) {
  const w = wallClock(ms - 12 * 3600e3, tz);
  return zonedToUtc(w.year, w.month, w.day, 12, 0, tz);
}

export function dateInputValue(ms, tz) {
  const w = wallClock(ms, tz);
  const p = (n) => String(n).padStart(2, "0");
  return `${w.year}-${p(w.month)}-${p(w.day)}`;
}

export function timeInputValue(ms, tz) {
  const w = wallClock(ms, tz);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(w.hour)}:${p(w.minute)}`;
}
