// Calendar math in the device's own time zone, and the words a card uses for when a plant needs water.
export const DAY = 86400000;

export function startOfDay(t) {
  const d = new Date(t);
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

export function addDays(t, n) {
  const d = new Date(t);
  d.setDate(d.getDate() + n);
  return d.getTime();
}

export function daysBetween(a, b) {
  return Math.round((startOfDay(b) - startOfDay(a)) / DAY);
}

/** The first moment of the day a plant last watered at `last` is due again. */
export function dueStart(last, interval) {
  return addDays(startOfDay(last), interval);
}

/** The ring's drained share: 0 at the watering, 1 at the start of the due day, past 1 once overdue. */
export function fraction(last, interval, now) {
  const due = dueStart(last, interval);
  return Math.max(0, (now - last) / (due - last));
}

const weekday = new Intl.DateTimeFormat("en-US", { weekday: "long" });
const weekdayShort = new Intl.DateTimeFormat("en-US", { weekday: "short" });
const longDate = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" });
const shortDate = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });
const monthDay = new Intl.DateTimeFormat("en-US", { month: "long", day: "numeric" });

export const fmt = {
  weekday: (t) => weekday.format(t),
  dow: (t) => weekdayShort.format(t),
  long: (t) => longDate.format(t),
  short: (t) => shortDate.format(t),
  monthDay: (t) => monthDay.format(t),
};

/** Where a plant stands today: thirsty, soon (70 % or more drained), fresh (watered today), or ok. */
export function standing(last, interval, now) {
  const f = fraction(last, interval, now);
  const due = dueStart(last, interval);
  const dueIn = daysBetween(now, due);
  const wateredAgo = daysBetween(last, now);
  if (dueIn <= 0) {
    const text = dueIn === 0 ? "Thirsty today" : dueIn === -1 ? "Thirsty since yesterday" : `Thirsty for ${-dueIn} days`;
    return { f, due, dueIn, state: "thirsty", text };
  }
  const when = dueIn === 1 ? "Due tomorrow" : dueIn < 7 ? `Due ${fmt.weekday(due)}` : `Due in ${dueIn} days`;
  if (wateredAgo === 0) return { f, due, dueIn, state: "fresh", text: "Watered today", next: when };
  return { f, due, dueIn, state: f >= 0.7 ? "soon" : "ok", text: when };
}

/** "today", "yesterday", "3 days ago". */
export function ago(t, now) {
  const n = daysBetween(t, now);
  return n === 0 ? "today" : n === 1 ? "yesterday" : `${n} days ago`;
}

/** A yyyy-mm-dd string for a date input, in local time. */
export function inputDate(t) {
  const d = new Date(t);
  const p = (v) => String(v).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
