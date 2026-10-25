import type { Metric, Point } from "@/lib/config"

const formatters = new Map<string, Intl.NumberFormat>()

function numberFormat(options: Intl.NumberFormatOptions): Intl.NumberFormat {
  const key = JSON.stringify(options)
  let formatter = formatters.get(key)
  if (!formatter) {
    formatter = new Intl.NumberFormat(undefined, options)
    formatters.set(key, formatter)
  }
  return formatter
}

/** The decimals a metric's readings are written with, at most two, so a count-up and the final value share a width. */
export function decimalsOf(history: Point[]): number {
  let decimals = 0
  for (const point of history) {
    const text = String(point.value)
    const dot = text.indexOf(".")
    if (dot >= 0) decimals = Math.max(decimals, Math.min(2, text.length - dot - 1))
  }
  return decimals
}

export function formatDuration(totalSeconds: number): string {
  const seconds = Math.max(0, Math.round(totalSeconds))
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, "0")}m`
  if (minutes > 0) return `${minutes}m ${String(rest).padStart(2, "0")}s`
  return `${rest}s`
}

export function formatValue(metric: Metric, value: number, decimals: number): string {
  switch (metric.format) {
    case "currency":
      return numberFormat({
        style: "currency",
        currency: metric.unit || "USD",
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      }).format(value)
    case "percent":
      return `${numberFormat({ minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value)}%`
    case "duration":
      return formatDuration(value)
    default:
      if (Math.abs(value) >= 1_000_000) {
        return numberFormat({ notation: "compact", maximumFractionDigits: 1 }).format(value)
      }
      return numberFormat({ minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value)
  }
}

/** A short axis label: $48K, 1.3K, 97%, 2h. */
export function formatAxis(metric: Metric, value: number): string {
  switch (metric.format) {
    case "currency":
      return numberFormat({ style: "currency", currency: metric.unit || "USD", notation: "compact", maximumFractionDigits: 1 }).format(value)
    case "percent":
      return `${numberFormat({ maximumFractionDigits: 1 }).format(value)}%`
    case "duration":
      return formatDuration(value)
    default:
      return numberFormat({ notation: "compact", maximumFractionDigits: 1 }).format(value)
  }
}

export function parseDate(date: string): Date {
  return /^\d{4}-\d{2}-\d{2}$/.test(date) ? new Date(`${date}T12:00:00`) : new Date(date)
}

export function formatDay(date: string): string {
  return parseDate(date).toLocaleDateString(undefined, { month: "short", day: "numeric" })
}

export function formatLongDay(date: string): string {
  return parseDate(date).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })
}

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" })

export function formatRelative(from: Date, now: Date): string {
  const minutes = Math.round((from.getTime() - now.getTime()) / 60000)
  if (Math.abs(minutes) < 60) return relative.format(minutes, "minute")
  const hours = Math.round(minutes / 60)
  if (Math.abs(hours) < 24) return relative.format(hours, "hour")
  return relative.format(Math.round(hours / 24), "day")
}
