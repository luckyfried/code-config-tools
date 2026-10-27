// Every conversion goes through the browser's own zone database with Intl.DateTimeFormat; nothing is shipped.
const HOUR = 3600e3;
const formats = new Map();

function format(zone) {
  let f = formats.get(zone);
  if (!f) {
    f = new Intl.DateTimeFormat("en-US", {
      timeZone: zone, hourCycle: "h23", weekday: "short",
      year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
    formats.set(zone, f);
  }
  return f;
}

/** The wall clock in `zone` at instant `ms`: y, mo, d, h, mi, s, and wd (Mon, Tue, ...). */
export function wall(zone, ms) {
  const out = {};
  for (const p of format(zone).formatToParts(ms)) {
    if (p.type === "weekday") out.wd = p.value;
    else if (p.type !== "literal") out[p.type] = Number(p.value);
  }
  return { y: out.year, mo: out.month, d: out.day, h: out.hour % 24, mi: out.minute, s: out.second, wd: out.wd };
}

/** Minutes `zone` is ahead of UTC at instant `ms`. */
export function offsetMin(zone, ms) {
  const t = Math.floor(ms / 1000) * 1000;
  const w = wall(zone, t);
  return Math.round((Date.UTC(w.y, w.mo - 1, w.d, w.h, w.mi, w.s) - t) / 60000);
}

/** The instant of 00:00 on the date "YYYY-MM-DD" in `zone`. */
export function midnight(zone, iso) {
  const [y, m, d] = iso.split("-").map(Number);
  const guess = Date.UTC(y, m - 1, d);
  let t = guess - offsetMin(zone, guess) * 60000;
  const second = offsetMin(zone, t);
  t = guess - second * 60000;
  return t;
}

export function isoDate(zone, ms) {
  const w = wall(zone, ms);
  return `${w.y}-${String(w.mo).padStart(2, "0")}-${String(w.d).padStart(2, "0")}`;
}

export function addDays(iso, n) {
  const [y, m, d] = iso.split("-").map(Number);
  const t = new Date(Date.UTC(y, m - 1, d + n));
  return t.toISOString().slice(0, 10);
}

/** Minute of the local day (0 to 1439) in `zone` at instant `ms`. */
export function localMinute(zone, ms) {
  const w = wall(zone, ms);
  return w.h * 60 + w.mi;
}

/** "15:00" or "3:00 pm". */
export function clock(h, mi, hourFormat) {
  const mm = String(mi).padStart(2, "0");
  if (hourFormat === 12) {
    const h12 = h % 12 === 0 ? 12 : h % 12;
    return `${h12}:${mm} ${h < 12 ? "am" : "pm"}`;
  }
  return `${String(h).padStart(2, "0")}:${mm}`;
}

/** A short hour mark for the axis and the strips: "09" or "9 am". */
export function hourMark(h, hourFormat) {
  if (hourFormat === 12) {
    if (h === 12) return "noon";
    return `${h % 12 === 0 ? 12 : h % 12} ${h < 12 ? "am" : "pm"}`;
  }
  return String(h).padStart(2, "0");
}

/** "5 h", "4½ h", or "5 h 45 min" for a difference in minutes. */
export function span(minutes) {
  const a = Math.abs(minutes);
  const h = Math.floor(a / 60);
  const m = a % 60;
  if (m === 0) return `${h} h`;
  if (m === 30) return `${h}½ h`;
  return h ? `${h} h ${m} min` : `${m} min`;
}

/** "5 h behind", "4½ h ahead", or "your time". */
export function relWords(minutes) {
  if (minutes === 0) return "same time as you";
  return `${span(minutes)} ${minutes > 0 ? "ahead" : "behind"}`;
}

export function inWindow(minute, start, end) {
  const s = Math.round(start * 60) % 1440;
  const e = Math.round(end * 60) % 1440;
  return s < e ? minute >= s && minute < e : minute >= s || minute < e;
}

export { HOUR };
