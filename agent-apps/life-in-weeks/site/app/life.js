// The calendar of a life: each row is a year of age that starts on a birthday, each column a week since it.
// The same rules as scripts/run.py, so the page and the run agree on every cell.

export const WEEKS = 52;
const DAY_MS = 86400000;

/** Days since 1970-01-01 for a calendar day, free of time zones and daylight saving. */
export function dayNumber(y, m, d) {
  return Math.round(Date.UTC(y, m - 1, d) / DAY_MS);
}

export function fromDayNumber(n) {
  const date = new Date(n * DAY_MS);
  return { y: date.getUTCFullYear(), m: date.getUTCMonth() + 1, d: date.getUTCDate() };
}

function isLeap(y) {
  return (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
}

function lastOfMonth(y, m) {
  return [31, isLeap(y) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];
}

/** A day from YYYY, YYYY-MM, or YYYY-MM-DD: the first day of that span, or its last with end = true. */
export function parseDay(text, end = false) {
  const match = /^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(String(text ?? "").trim());
  if (!match) return null;
  const y = Number(match[1]);
  const m = match[2] ? Number(match[2]) : null;
  const d = match[3] ? Number(match[3]) : null;
  if (m === null) return end ? dayNumber(y, 12, 31) : dayNumber(y, 1, 1);
  if (m < 1 || m > 12) return null;
  if (d === null) return end ? dayNumber(y, m, lastOfMonth(y, m)) : dayNumber(y, m, 1);
  if (d < 1 || d > lastOfMonth(y, m)) return null;
  return dayNumber(y, m, d);
}

export function today() {
  const now = new Date();
  return dayNumber(now.getFullYear(), now.getMonth() + 1, now.getDate());
}

export function todayIso() {
  const t = fromDayNumber(today());
  return `${t.y}-${String(t.m).padStart(2, "0")}-${String(t.d).padStart(2, "0")}`;
}

/** The life on a calendar: born is YYYY-MM-DD, rows the years of age the grid holds. */
export function lifeOf(born, rows) {
  const b = fromDayNumber(parseDay(born));
  const birthday = (age) => {
    const y = b.y + age;
    return b.m === 2 && b.d === 29 && !isLeap(y) ? dayNumber(y, 3, 1) : dayNumber(y, b.m, b.d);
  };
  const cells = rows * WEEKS;
  const last = birthday(rows) - 1;

  /** The cell index of a day. */
  const cellOf = (day) => {
    const y = fromDayNumber(day).y;
    let age = y - b.y;
    if (day < birthday(age)) age -= 1;
    const week = Math.min(WEEKS - 1, Math.floor((day - birthday(age)) / 7));
    return age * WEEKS + week;
  };

  /** The first and last day of a cell. */
  const spanOf = (cell) => {
    const age = Math.floor(cell / WEEKS);
    const week = cell % WEEKS;
    const first = birthday(age) + week * 7;
    const lastDay = week === WEEKS - 1 ? birthday(age + 1) - 1 : first + 6;
    return { first, last: lastDay, age, week };
  };

  return { rows, cells, first: birthday(0), last, birthday, cellOf, spanOf };
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

/** "3 – 9 Mar 2025", "28 Feb – 6 Mar 2025", "29 Dec 2025 – 4 Jan 2026". */
export function rangeWords(first, last) {
  const a = fromDayNumber(first);
  const z = fromDayNumber(last);
  if (a.y !== z.y) return `${a.d} ${MONTHS[a.m - 1]} ${a.y} – ${z.d} ${MONTHS[z.m - 1]} ${z.y}`;
  if (a.m !== z.m) return `${a.d} ${MONTHS[a.m - 1]} – ${z.d} ${MONTHS[z.m - 1]} ${z.y}`;
  return `${a.d} – ${z.d} ${MONTHS[z.m - 1]} ${z.y}`;
}

/** "14 March 1991". */
export function longDate(day) {
  const t = fromDayNumber(day);
  return `${t.d} ${MONTHS_LONG[t.m - 1]} ${t.y}`;
}

export function yearOf(day) {
  return fromDayNumber(day).y;
}

export const count = new Intl.NumberFormat("en-US");

export function ordinal(n) {
  const tail = n % 100;
  if (tail >= 11 && tail <= 13) return `${n}th`;
  return `${n}${["th", "st", "nd", "rd"][n % 10] ?? "th"}`;
}
