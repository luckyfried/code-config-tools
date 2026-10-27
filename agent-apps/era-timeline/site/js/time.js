// Dates, the semantic axis levels, and the words a date is shown in. Time is milliseconds since 1970 (UTC), so a
// pin at 500 BCE and one on 2 May 1911 sit on one number line.

export const DAY = 86400000;
export const YEAR = 365.2425 * DAY;
export const MONTH = YEAR / 12;

const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DATE = /^(-?)(\d{1,4})(?:-(\d{2})(?:-(\d{2}))?)?$/;

/** Milliseconds at the start of a UTC day; years 0 to 99 and before the common era included. */
export function utc(year, month = 0, day = 1) {
  const date = new Date(Date.UTC(2000, 0, 1));
  date.setUTCFullYear(year, month, day);
  return date.getTime();
}

/** The parts of `t`: astronomical year, month 0 to 11, day 1 to 31. */
export function parts(t) {
  const date = new Date(t);
  return { year: date.getUTCFullYear(), month: date.getUTCMonth(), day: date.getUTCDate() };
}

/**
 * A date string ("1911", "1911-05", "1911-05-02", "-500" for 500 BCE) as `{t, end, precision}`: `t` the start of the
 * period it names, `end` the start of the next one.
 */
export function parseDate(text) {
  const found = DATE.exec(String(text).trim());
  if (!found) return null;
  let year = Number(found[2]);
  if (found[1]) year = 1 - year;
  const month = found[3] ? Number(found[3]) - 1 : null;
  const day = found[4] ? Number(found[4]) : null;
  if (month === null) return { t: utc(year), end: utc(year + 1), precision: "year", year };
  if (day === null) return { t: utc(year, month), end: utc(year, month + 1), precision: "month", year };
  return { t: utc(year, month, day), end: utc(year, month, day + 1), precision: "day", year };
}

export const yearWords = (year) => (year > 0 ? String(year) : `${1 - year} BCE`);

/** A date in American words at its own precision: "May 2, 1911", "May 1911", "1911", "500 BCE". */
export function dateWords(t, precision) {
  const { year, month, day } = parts(t);
  if (precision === "year") return yearWords(year);
  if (precision === "month") return `${MONTHS[month]} ${yearWords(year)}`;
  return `${MONTHS[month]} ${day}, ${yearWords(year)}`;
}

/** The span between two dates in plain words: "3 days", "8 months", "21 years". */
export function spanWords(ms) {
  const days = Math.round(ms / DAY);
  if (days < 1) return "the same day";
  if (days < 60) return days === 1 ? "1 day" : `${days} days`;
  const months = Math.round(ms / MONTH);
  if (months < 24) return `${months} months`;
  const years = Math.round(ms / YEAR);
  return `${years} years`;
}

/**
 * Every step the axis can label at, finest first. `level` is the semantic level the axis reports (its data-level),
 * `unit` how ticks are counted, `n` how many units a step is.
 */
export const STEPS = [
  { level: "day", unit: "day", n: 1 },
  { level: "day", unit: "day", n: 2 },
  { level: "day", unit: "day", n: 7 },
  { level: "month", unit: "month", n: 1 },
  { level: "month", unit: "month", n: 3 },
  { level: "month", unit: "month", n: 6 },
  { level: "year", unit: "year", n: 1 },
  { level: "year", unit: "year", n: 2 },
  { level: "year", unit: "year", n: 5 },
  { level: "decade", unit: "year", n: 10 },
  { level: "decade", unit: "year", n: 20 },
  { level: "century", unit: "year", n: 50 },
  { level: "century", unit: "year", n: 100 },
  { level: "century", unit: "year", n: 200 },
  { level: "century", unit: "year", n: 500 },
  { level: "century", unit: "year", n: 1000 },
  { level: "century", unit: "year", n: 2000 },
];

const stepMs = (step) => step.n * (step.unit === "day" ? DAY : step.unit === "month" ? MONTH : YEAR);

/** The finest step whose ticks sit at least `minPx` apart when one pixel is `msPerPx`. */
export function pickStep(msPerPx, minPx) {
  return STEPS.find((step) => stepMs(step) / msPerPx >= minPx) ?? STEPS[STEPS.length - 1];
}

/** The tick label for `t` at `step`. */
export function tickWords(t, step) {
  const { year, month, day } = parts(t);
  if (step.level === "day") return String(day);
  if (step.level === "month") return MONTHS_SHORT[month];
  if (step.level === "decade") return year > 0 ? `${year}s` : yearWords(year);
  return yearWords(year);
}

/**
 * Whether a tick opens the larger unit around it (January, the first of a month, a decade, a century), and the words
 * it takes when it stands for that unit too ("1911" for January, "May" for the first).
 */
export function majorOf(t, step) {
  const { year, month, day } = parts(t);
  if (step.level === "day") return day === 1 ? MONTHS_SHORT[month] : null;
  if (step.level === "month") return month === 0 ? yearWords(year) : null;
  if (step.level === "year") return year % 10 === 0 ? yearWords(year) : null;
  if (step.level === "decade") return year % 100 === 0 ? tickWords(t, step) : null;
  return year % 1000 === 0 ? yearWords(year) : null;
}

/** The ticks of `step` from `t0` to `t1`: `[{t, key, words, major}]`. */
export function ticks(t0, t1, step) {
  const out = [];
  const start = parts(t0);
  const push = (t) => out.push({ t, key: `${step.level}:${t}`, words: tickWords(t, step), major: majorOf(t, step) });
  if (step.unit === "year") {
    let year = Math.floor(start.year / step.n) * step.n;
    for (let t = utc(year); t <= t1 && out.length < 400; year += step.n, t = utc(year)) push(t);
  } else if (step.unit === "month") {
    let year = start.year;
    let month = start.month - (start.month % step.n);
    for (let t = utc(year, month); t <= t1 && out.length < 400; ) {
      push(t);
      month += step.n;
      if (month > 11) {
        month -= 12;
        year += 1;
      }
      t = utc(year, month);
    }
  } else {
    const keep = step.n === 1 ? () => true : step.n === 2 ? (d) => d % 2 === 1 && d < 31 : (d) => d === 1 || d === 8 || d === 15 || d === 22;
    let { year, month, day } = start;
    for (let t = utc(year, month, day); t <= t1 && out.length < 400; ) {
      if (keep(day)) push(t);
      t = utc(year, month, day + 1);
      ({ year, month, day } = parts(t));
    }
  }
  return out;
}

/**
 * The context row under the ticks: the larger unit around them ("1911" over months, "May 1911" over days), one
 * label per boundary, starting with the one already in force at `t0`. None above the month level.
 */
export function contextTicks(t0, t1, step) {
  const out = [];
  const start = parts(t0);
  if (step.level === "month") {
    for (let year = start.year; utc(year) <= t1 && out.length < 200; year += 1) {
      const t = utc(year);
      out.push({ t, key: `ctx-y:${t}`, words: yearWords(year) });
    }
  } else if (step.level === "day") {
    let { year, month } = start;
    for (let t = utc(year, month); t <= t1 && out.length < 200; ) {
      out.push({ t, key: `ctx-m:${t}`, words: `${MONTHS[month]} ${yearWords(year)}` });
      month += 1;
      if (month > 11) {
        month = 0;
        year += 1;
      }
      t = utc(year, month);
    }
  }
  return out;
}
