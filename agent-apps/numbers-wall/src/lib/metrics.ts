import type { Metric } from "@/lib/config"
import { decimalsOf, formatValue } from "@/lib/format"

export type Direction = "up" | "down" | "flat"

export type Delta = {
  /** The change between the last two readings, in the metric's own units. */
  change: number
  direction: Direction
  good: boolean | null
  text: string
  spoken: string
  since: string
}

const SPARK_POINTS = 30

export function latest(metric: Metric) {
  return metric.history.at(-1)
}

export function sparkPoints(metric: Metric) {
  return metric.history.slice(-SPARK_POINTS)
}

export function deltaOf(metric: Metric): Delta | null {
  const { history } = metric
  if (history.length < 2) return null
  const last = history[history.length - 1].value
  const prev = history[history.length - 2].value
  const change = Number((last - prev).toFixed(10))
  const direction: Direction = change > 0 ? "up" : change < 0 ? "down" : "flat"
  const good = direction === "flat" ? null : (direction === "up") === metric.higherIsBetter
  const arrow = direction === "up" ? "▲" : direction === "down" ? "▼" : ""
  let amount: string
  let spokenAmount: string
  if (metric.format === "percent") {
    const points = Math.abs(change).toFixed(Math.max(1, decimalsOf(history)))
    amount = `${points} pt`
    spokenAmount = `${points} points`
  } else if (prev !== 0) {
    const ratio = Math.abs(change / prev) * 100
    const pct = ratio >= 100 ? ratio.toFixed(0) : ratio.toFixed(1)
    amount = `${pct}%`
    spokenAmount = `${pct} percent`
  } else {
    amount = formatValue(metric, Math.abs(change), decimalsOf(history))
    spokenAmount = amount
  }
  const since = history[history.length - 2].date
  if (direction === "flat") {
    return { change, direction, good, text: "No change", spoken: "No change", since }
  }
  return {
    change,
    direction,
    good,
    text: `${arrow} ${amount}`,
    spoken: `${direction === "up" ? "Up" : "Down"} ${spokenAmount}`,
    since,
  }
}

export function goalMet(metric: Metric): boolean {
  const point = latest(metric)
  if (metric.goal == null || !point) return false
  return metric.higherIsBetter ? point.value >= metric.goal : point.value <= metric.goal
}

/** The y range of a chart: the readings and the goal, with a little air above and below. */
export function domainOf(values: number[], goal: number | null | undefined): [number, number] {
  let min = Math.min(...values)
  let max = Math.max(...values)
  if (goal != null) {
    min = Math.min(min, goal)
    max = Math.max(max, goal)
  }
  const pad = (max - min || Math.abs(max) || 1) * 0.12
  return [min - pad, max + pad]
}
