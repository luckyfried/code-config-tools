// An example year for a first open: seasons that lift into summer, better weekends, runs of good and rough
// stretches, a few missed days, and a note on some days. The same year always gives the same picture.
import { yearDays, parse } from "./dates.js";

const NOTES = {
  1: ["Flu, stayed in bed", "Missed the train and the meeting", "Couldn't sleep", "Bad news from home", "Everything took twice as long"],
  2: ["Grey all day", "Too many meetings", "Tired, early night", "Cold commute in the rain", "Argued about nothing"],
  3: ["Quiet day", "Groceries and laundry", "Worked from home", "Long day at the desk", "Nothing much, and that was fine"],
  4: ["Long walk by the river", "Dinner with Sam", "Finished the book", "Good run before work", "Lunch outside in the sun"],
  5: ["Lake swim at sunset", "Concert with old friends", "Shipped the project", "Beach day, no phones", "Iris laughed all through dinner"],
};

function random(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Days before `until` (an ISO day) in `year`, colored.
export function exampleYear(year, until) {
  const rand = random(year * 7919);
  const days = {};
  let drift = 0;
  yearDays(year).forEach(({ day }, i) => {
    if (day >= until) return;
    drift = drift * 0.75 + (rand() - 0.5) * 2.1;
    if (rand() < 0.05) return;
    const season = 0.95 * Math.sin((2 * Math.PI * (i - 95)) / 365);
    const weekday = parse(day).getDay();
    const weekend = weekday === 0 || weekday === 6 ? 0.45 : weekday === 1 ? -0.3 : 0;
    const level = Math.max(1, Math.min(5, Math.round(2.95 + season + weekend + drift)));
    const entry = { mood: level };
    if (rand() < 0.14) {
      const list = NOTES[level];
      entry.note = list[Math.floor(rand() * list.length)];
    }
    days[day] = entry;
  });
  return days;
}
