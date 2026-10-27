import { format, isThisYear, parseISO } from "date-fns"
import { config } from "@/config"

const whole = new Intl.NumberFormat(undefined, { style: "currency", currency: config.currency, maximumFractionDigits: 0 })
const compact = new Intl.NumberFormat(undefined, { style: "currency", currency: config.currency, notation: "compact", maximumFractionDigits: 1 })

/** Money in whole units of the board's currency: "$48,000". */
export const money = (value: number) => whole.format(Math.round(value))

/** Money in short form for tight places: "$1.2M", "$48K". */
export const shortMoney = (value: number) => compact.format(value)

/** A next-step date as a person reads it: "Oct 30", or "Oct 30, 2027" outside this year. */
export function dayLabel(iso: string): string {
  if (!iso) return ""
  const date = parseISO(iso)
  return format(date, isThisYear(date) ? "MMM d" : "MMM d, yyyy")
}

export function when(ms: number, now: number): string {
  const days = Math.floor((now - ms) / 86_400_000)
  if (days < 1) return new Date(ms).toDateString() === new Date(now).toDateString() ? "today" : "yesterday"
  if (days === 1) return "yesterday"
  if (days < 7) return `${days} days ago`
  return format(ms, isThisYear(ms) ? "MMM d" : "MMM d, yyyy")
}

function hashOf(name: string): number {
  let hash = 0
  for (const char of name.toLowerCase()) hash = (hash * 31 + char.charCodeAt(0)) >>> 0
  return hash
}

/** A steady hue for a company's mark, from its name. */
export const hueOf = (name: string) => hashOf(name) % 360

/** Which of the mark's four shapes a company gets, from its name. */
export const shapeOf = (name: string) => Math.floor(hashOf(name) / 360) % 4

export const initialOf = (name: string) => (name.trim().match(/[\p{L}\p{N}]/u)?.[0] ?? "?").toUpperCase()

export const plural = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`
