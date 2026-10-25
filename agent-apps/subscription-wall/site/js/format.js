// Money and date helpers. Dates are calendar days written YYYY-MM-DD and handled as local noon so no time zone
// shift ever moves a charge to another day.

export const PER_YEAR = { week: 52, month: 12, year: 1 };
const EVERY_WORD = { week: "a week", month: "a month", year: "a year" };
const EVERY_BADGE = { week: "Weekly", month: "Monthly", year: "Yearly" };

export function moneyFormat(currency) {
  const full = new Intl.NumberFormat(undefined, { style: "currency", currency });
  const whole = new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0, minimumFractionDigits: 0 });
  return {
    cents: (c) => full.format(c / 100),
    round: (c) => whole.format(Math.round(c / 100)),
  };
}

// Yellow and lime hues, which read muddy at a dark theme's lightness; the themes lift them and ink them dark.
export const bright = (hue) => hue >= 70 && hue <= 130;

export const everyWord = (every) => EVERY_WORD[every];
export const everyBadge = (every) => EVERY_BADGE[every];

export function parseDay(text) {
  const [y, m, d] = text.split("-").map(Number);
  return new Date(y, m - 1, d, 12);
}

export function isoDay(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function todayLocal() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), 12);
}

export const daysBetween = (a, b) => Math.round((b - a) / 86400000);

function addMonths(date, months, anchorDay) {
  const total = date.getFullYear() * 12 + date.getMonth() + months;
  const year = Math.floor(total / 12);
  const month = total % 12;
  const last = new Date(year, month + 1, 0).getDate();
  return new Date(year, month, Math.min(anchorDay, last), 12);
}

// The charge n periods after `from` (n may be negative), keeping a monthly charge on its anchor day.
export function step(from, every, anchorDay, n) {
  if (every === "week") return new Date(from.getFullYear(), from.getMonth(), from.getDate() + 7 * n, 12);
  const months = every === "year" ? 12 * n : n;
  return addMonths(from, months, anchorDay);
}

// The first charge on or after today and the one before it.
export function chargeWindow(sub, today) {
  let next = parseDay(sub.nextCharge);
  let i = 0;
  while (next < today && i < 1000) {
    i += 1;
    next = step(parseDay(sub.nextCharge), sub.every, sub.day, i);
  }
  const prev = step(next, sub.every, sub.day, -1);
  return { next, prev };
}

const shortDate = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
const monthShort = new Intl.DateTimeFormat(undefined, { month: "short" });
const monthLong = new Intl.DateTimeFormat(undefined, { month: "long", year: "numeric" });
const monthOnly = new Intl.DateTimeFormat(undefined, { month: "long" });
const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });

export const fmtShort = (d) => shortDate.format(d);
export const fmtMonthShort = (d) => monthShort.format(d);
export const fmtMonthLong = (d) => monthLong.format(d);
export const fmtMonthOnly = (d) => monthOnly.format(d);

export function fmtUntil(days) {
  if (days < 45) return relative.format(days, "day");
  return relative.format(Math.round(days / 30.44), "month");
}

export function listJoin(names) {
  return new Intl.ListFormat("en", { style: "long", type: "conjunction" }).format(names);
}

export function plural(n, one, many) {
  return `${n} ${n === 1 ? one : many}`;
}
