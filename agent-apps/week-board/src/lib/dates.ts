import { addDays, format, isWeekend, parseISO, startOfWeek } from "date-fns"

export type WeekStart = "mon" | "sun"
export type DayKey = string

export const LATER = "later"

export function toKey(d: Date): DayKey {
  return format(d, "yyyy-MM-dd")
}

export function fromKey(k: DayKey): Date {
  return parseISO(k)
}

/** The board's clock. `?today=2026-10-23` sets the date; the time of day stays the device's. */
export function readToday(): Date {
  const now = new Date()
  const asked = new URLSearchParams(window.location.search).get("today")
  if (asked && /^\d{4}-\d{2}-\d{2}$/.test(asked)) {
    const d = parseISO(asked)
    if (!Number.isNaN(d.getTime())) {
      d.setHours(now.getHours(), now.getMinutes(), now.getSeconds())
      return d
    }
  }
  return now
}

export interface WeekView {
  /** The days shown as columns, in order. */
  days: DayKey[]
  /** The day undone cards carry into: today, or the next shown day when today is a weekend off the board. */
  anchor: DayKey
  /** Today's date key, shown or not. */
  today: DayKey
}

export function weekView(now: Date, weekStart: WeekStart, columns: 5 | 7): WeekView {
  const today = toKey(now)
  let anchorDate = now
  if (columns === 5) {
    while (isWeekend(anchorDate)) anchorDate = addDays(anchorDate, 1)
  }
  const start = startOfWeek(anchorDate, { weekStartsOn: weekStart === "sun" ? 0 : 1 })
  const all = Array.from({ length: 7 }, (_, i) => addDays(start, i))
  const shown = columns === 5 ? all.filter((d) => !isWeekend(d)) : all
  return { days: shown.map(toKey), anchor: toKey(anchorDate), today }
}

export function weekdayLong(k: DayKey): string {
  return format(fromKey(k), "EEEE")
}

export function weekdayShort(k: DayKey): string {
  return format(fromKey(k), "EEE")
}

export function dayOfMonth(k: DayKey): string {
  return format(fromKey(k), "d")
}

export function rangeLabel(days: DayKey[]): string {
  const a = fromKey(days[0])
  const b = fromKey(days[days.length - 1])
  if (a.getMonth() === b.getMonth()) return `${format(a, "MMMM d")} to ${format(b, "d")}`
  return `${format(a, "MMM d")} to ${format(b, "MMM d")}`
}

/** Where the day stands, 0 at 6 AM and 1 at midnight, for the now marker. */
export function dayProgress(now: Date): number {
  const minutes = now.getHours() * 60 + now.getMinutes() - 6 * 60
  return Math.min(1, Math.max(0, minutes / (18 * 60)))
}
