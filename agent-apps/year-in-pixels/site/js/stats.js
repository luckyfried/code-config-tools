// Counts, runs, the best month, and the week's shape for one year of days.
import { MONTHS, WEEKDAYS, yearDays, parse } from "./dates.js";

export function yearStats(days, year, weekStart) {
  const counts = [0, 0, 0, 0, 0, 0];
  const runs = [null, null, null, null, null, null];
  const months = Array.from({ length: 12 }, () => ({ sum: 0, n: 0, high: 0, counts: [0, 0, 0, 0, 0, 0] }));
  const week = Array.from({ length: 7 }, () => ({ sum: 0, n: 0 }));
  let run = { mood: 0, len: 0, start: null };
  let total = 0;

  for (const { day, month } of yearDays(year)) {
    const entry = days[day];
    const mood = entry ? entry.mood : 0;
    if (mood) {
      total++;
      counts[mood]++;
      const m = months[month];
      m.sum += mood;
      m.n++;
      m.counts[mood]++;
      if (mood >= 4) m.high++;
      const w = week[parse(day).getDay()];
      w.sum += mood;
      w.n++;
    }
    if (mood && mood === run.mood) run.len++;
    else run = { mood, len: mood ? 1 : 0, start: day };
    if (mood && (!runs[mood] || run.len > runs[mood].len)) runs[mood] = { len: run.len, start: run.start, end: day };
  }

  let best = null;
  months.forEach((m, i) => {
    if (m.n >= 5 && (!best || m.sum / m.n > best.avg)) best = { month: i, name: MONTHS[i], avg: m.sum / m.n, high: m.high, n: m.n };
  });

  const order = weekStart === "sun" ? [0, 1, 2, 3, 4, 5, 6] : [1, 2, 3, 4, 5, 6, 0];
  const weekdays = order.map((d) => ({ name: WEEKDAYS[d], avg: week[d].n ? week[d].sum / week[d].n : 0 }));

  return { total, counts, runs, months, best, weekdays };
}
