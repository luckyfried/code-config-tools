// Local-calendar date helpers; a day is always the ISO string YYYY-MM-DD in the person's own time zone.
export const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export const SHORT_MONTHS = MONTHS.map((m) => m.slice(0, 3));
export const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
export const DAY_RE = /^\d{4}-\d{2}-\d{2}$/;

const pad = (n) => String(n).padStart(2, "0");

export const iso = (year, month, day) => `${year}-${pad(month + 1)}-${pad(day)}`;
export const daysIn = (year, month) => new Date(year, month + 1, 0).getDate();
export const parse = (day) => {
  const [y, m, d] = day.split("-").map(Number);
  return new Date(y, m - 1, d);
};
export const todayIso = () => {
  const t = new Date();
  return iso(t.getFullYear(), t.getMonth(), t.getDate());
};
export const longDate = (day) => parse(day).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
export const shortDate = (day) => parse(day).toLocaleDateString("en-US", { month: "short", day: "numeric" });
export const yearOf = (day) => Number(day.slice(0, 4));

// Every day of a year in calendar order, as { day, month (0-11), date (1-31) }.
export function yearDays(year) {
  const out = [];
  for (let m = 0; m < 12; m++) {
    for (let d = 1; d <= daysIn(year, m); d++) out.push({ day: iso(year, m, d), month: m, date: d });
  }
  return out;
}

export function addDays(day, n) {
  const t = parse(day);
  t.setDate(t.getDate() + n);
  return iso(t.getFullYear(), t.getMonth(), t.getDate());
}
