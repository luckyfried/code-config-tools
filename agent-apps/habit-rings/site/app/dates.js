// Calendar days in the device's own time zone, keyed "YYYY-MM-DD" as the stored days are.
const pad = (n) => String(n).padStart(2, "0");

export const dayKey = (date) => `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

export const startOfDay = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate());

export const addDays = (date, n) => new Date(date.getFullYear(), date.getMonth(), date.getDate() + n);

export const daysBetween = (from, to) => Math.round((startOfDay(to) - startOfDay(from)) / 86400000);

const long = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" });
const short = new Intl.DateTimeFormat("en-US", { weekday: "long", month: "short", day: "numeric" });
const withYear = new Intl.DateTimeFormat("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
const month = new Intl.DateTimeFormat("en-US", { month: "short" });
const weekday = new Intl.DateTimeFormat("en-US", { weekday: "short" });

export const longDate = (date) => long.format(date);
export const shortDate = (date) => short.format(date);
export const tipDate = (date, today) => (date.getFullYear() === today.getFullYear() ? long.format(date) : withYear.format(date));
export const monthName = (date) => month.format(date);
export const weekdayName = (date) => weekday.format(date);

/** "8 pm", "noon", "midnight": how a person says the hour. */
export function hourWords(hour) {
  if (hour === 0) return "midnight";
  if (hour === 12) return "noon";
  return hour < 12 ? `${hour} am` : `${hour - 12} pm`;
}

export function partOfDay(date) {
  const hour = date.getHours();
  if (hour < 5) return "evening";
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}
