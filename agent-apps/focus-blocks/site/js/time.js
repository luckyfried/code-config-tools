// Clock math and the words for times and durations.
export const SECOND = 1000;
export const MINUTE = 60 * SECOND;
export const HOUR = 60 * MINUTE;
export const DAY = 24 * HOUR;

export function startOfDay(t) {
  const d = new Date(t);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function addDays(dayStart, n) {
  const d = new Date(dayStart);
  d.setDate(d.getDate() + n);
  return d.getTime();
}

// The strip's window for the day that starts at midnight `day0`: dayStart to dayEnd hours, in local time.
export function windowOf(day0, cfg) {
  const from = new Date(day0);
  from.setHours(cfg.dayStart, 0, 0, 0);
  const to = new Date(day0);
  to.setHours(cfg.dayEnd, 0, 0, 0);
  return { from: from.getTime(), to: to.getTime() };
}

// "25:00", or "1:30:00" from an hour up; whole seconds rounded up, so the clock reads 00:00 only at the end.
export function clock(ms) {
  const total = Math.max(0, Math.ceil(ms / SECOND));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

// "50 min", "2 h 40 min", "3 h".
export function duration(ms) {
  const minutes = Math.round(ms / MINUTE);
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m} min`;
  return m === 0 ? `${h} h` : `${h} h ${m} min`;
}

// "2.5 h" for the week rows.
export function hours(ms) {
  const h = ms / HOUR;
  if (h === 0) return "0 h";
  return `${h < 10 ? h.toFixed(1).replace(/\.0$/, "") : Math.round(h)} h`;
}

const timeFmt = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" });
const hourFmt = new Intl.DateTimeFormat(undefined, { hour: "numeric" });
const weekdayFmt = new Intl.DateTimeFormat(undefined, { weekday: "short" });
const dateFmt = new Intl.DateTimeFormat("en-CA", { year: "numeric", month: "2-digit", day: "2-digit" });

export const timeOfDay = (t) => timeFmt.format(t);
export const hourLabel = (t) => hourFmt.format(t).replace(":00", "");
export const weekday = (t) => weekdayFmt.format(t);
export const isoDate = (t) => dateFmt.format(t);

export function greeting(now, name) {
  const h = new Date(now).getHours();
  const part = h < 5 ? "Good evening" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
  return name ? `${part}, ${name}` : part;
}
