import { differenceInCalendarDays, format, parseISO } from "date-fns"
import type { Season } from "./types"

export function today(): string {
  return format(new Date(), "yyyy-MM-dd")
}

export function daysSince(day: string, now = today()): number {
  return differenceInCalendarDays(parseISO(now), parseISO(day))
}

export function longDay(day: string): string {
  return format(parseISO(day), "EEEE, MMMM d")
}

export function shortDay(day: string): string {
  const d = parseISO(day)
  return format(d, d.getFullYear() === new Date().getFullYear() ? "MMM d" : "MMM d, yyyy")
}

export function seasonOf(day: string): Season {
  const m = parseISO(day).getMonth()
  if (m >= 2 && m <= 4) return "spring"
  if (m >= 5 && m <= 7) return "summer"
  if (m >= 8 && m <= 10) return "fall"
  return "winter"
}
