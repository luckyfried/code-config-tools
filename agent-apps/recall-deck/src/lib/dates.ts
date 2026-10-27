// Days are local calendar dates written YYYY-MM-DD, so "due today" means the person's today wherever they are.

export function dayKey(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${d.getFullYear()}-${m}-${day}`
}

export function parseDay(key: string): Date {
  const [y, m, d] = key.split("-").map(Number)
  return new Date(y, m - 1, d)
}

export function addDays(key: string, n: number): string {
  const d = parseDay(key)
  d.setDate(d.getDate() + n)
  return dayKey(d)
}

export function daysBetween(from: string, to: string): number {
  return Math.round((parseDay(to).getTime() - parseDay(from).getTime()) / 86_400_000)
}

export const today = (): string => dayKey(new Date())

const WEEKDAY = new Intl.DateTimeFormat("en-US", { weekday: "short" })
const MONTH_DAY = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" })

export const weekday = (key: string): string => WEEKDAY.format(parseDay(key))
export const monthDay = (key: string): string => MONTH_DAY.format(parseDay(key))

/** "today", "tomorrow", "in 6 days", "Nov 14"; a date in the past reads as today because it is due now. */
export function whenDue(due: string, now: string): string {
  const n = daysBetween(now, due)
  if (n <= 0) return "today"
  if (n === 1) return "tomorrow"
  if (n < 14) return `in ${n} days`
  return monthDay(due)
}

export function spanLabel(days: number): string {
  if (days < 1) return "today"
  if (days < 31) return `${days}d`
  if (days < 365) return `${Math.round(days / 30)}mo`
  return `${(days / 365).toFixed(1).replace(/\.0$/, "")}y`
}
