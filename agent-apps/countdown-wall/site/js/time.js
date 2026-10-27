// When each event is: its next occurrence, whether it has passed, and the parts of the time left or gone.

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;
const DAY = 86400000;
const HOUR = 3600000;
const MINUTE = 60000;

/** An ISO date or date and time; a date alone is local midnight and the event is all day. */
export function parseWhen(text) {
  const m = DATE_ONLY.exec(text);
  if (m) return { at: new Date(+m[1], +m[2] - 1, +m[3]), allDay: true };
  return { at: new Date(text), allDay: false };
}

/** The same moment in another year; February 29 becomes February 28. */
function inYear(date, year) {
  const d = new Date(date.getTime());
  d.setFullYear(year);
  if (d.getMonth() !== date.getMonth()) d.setDate(0);
  return d;
}

/** An all-day event lasts until 23:59 local; a timed one ends at its time. */
function endOf(at, allDay) {
  return allDay ? new Date(at.getFullYear(), at.getMonth(), at.getDate(), 23, 59, 59, 999) : at;
}

/**
 * The occurrence of `ev` that matters at `now`: `at` (when it starts), `end`, `start` (the progress bar's origin),
 * and whether it is past or happening today.
 */
export function occurrence(ev, now) {
  const first = parseWhen(ev.date);
  const allDay = first.allDay;
  let at = first.at;
  let start = ev.start ? parseWhen(ev.start).at : new Date(at.getTime() - 365 * DAY);
  if (ev.repeat === "yearly" && endOf(at, allDay) <= now) {
    let year = Math.max(at.getFullYear(), now.getFullYear() - 1);
    while (endOf(inYear(first.at, year), allDay) <= now) year += 1;
    at = inYear(first.at, year);
    start = inYear(first.at, year - 1);
  }
  const end = endOf(at, allDay);
  return {
    at,
    end,
    allDay,
    start,
    past: end <= now,
    today: allDay && now >= at && now <= end,
  };
}

/** Days, hours, minutes, and seconds in `ms`, which counts down (rounded up) or up (rounded down). */
export function parts(ms, up = false) {
  const total = Math.max(0, up ? Math.floor(ms / 1000) : Math.ceil(ms / 1000)) * 1000;
  return {
    days: Math.floor(total / DAY),
    hours: Math.floor((total % DAY) / HOUR),
    minutes: Math.floor((total % HOUR) / MINUTE),
    seconds: Math.floor((total % MINUTE) / 1000),
  };
}

/** What the hero's board shows: time to the start, or what is left of an all-day event today. */
export function remaining(occ, now) {
  if (occ.today) return parts(occ.end.getTime() + 1 - now.getTime());
  return parts(occ.at.getTime() - now.getTime());
}

/** How far through the wait we are, 0 to 1. */
export function progress(occ, now) {
  const span = occ.at.getTime() - occ.start.getTime();
  if (span <= 0) return 1;
  return Math.min(1, Math.max(0, (now.getTime() - occ.start.getTime()) / span));
}

export function daysUntil(occ, now) {
  return remaining(occ, now).days;
}

export function daysSince(occ, now) {
  return Math.floor((now.getTime() - occ.at.getTime()) / DAY);
}

export function formatters(hourFormat) {
  const hour12 = hourFormat !== 24;
  const long = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" });
  const longYear = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  const short = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric" });
  const shortYear = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" });
  const clock = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", hour12 });
  const sameYear = (d, now) => d.getFullYear() === now.getFullYear();
  // "7:40 AM" never breaks before its AM.
  const keep = (text) => text.replace(/\s(AM|PM)$/, "\u00a0$1");
  return {
    clock: (d) => keep(clock.format(d)),
    /** "Friday, November 13, 7:40 AM", or "Friday, December 25, all day". */
    long(occ, now) {
      const day = (sameYear(occ.at, now) ? long : longYear).format(occ.at);
      if (occ.today) return `Today, all day`;
      return occ.allDay ? `${day}, all day` : `${day}, ${keep(clock.format(occ.at))}`;
    },
    /** "Sat, Nov 21, 8:00 PM", with the year when it is not this one. */
    short(occ, now) {
      const day = sameYear(occ.at, now) ? short.format(occ.at) : shortYear.format(occ.at);
      return occ.allDay ? `${day}, all day` : `${day}, ${keep(clock.format(occ.at))}`;
    },
    since(occ) {
      return shortYear.format(occ.at);
    },
    today: (now) => `${long.format(now)}, ${keep(clock.format(now))}`,
  };
}
