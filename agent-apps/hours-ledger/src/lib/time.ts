import {
  addDays,
  eachDayOfInterval,
  endOfDay,
  endOfMonth,
  format,
  isSameDay,
  startOfDay,
  startOfMonth,
  startOfWeek,
} from "date-fns"
import { useEffect, useState } from "react"
import { weekStartsOn } from "./config"
import type { Entry } from "./store"

export const MINUTE = 60_000
export const HOUR = 60 * MINUTE

export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const tick = () => setNow(Date.now())
    const id = window.setInterval(tick, intervalMs)
    document.addEventListener("visibilitychange", tick)
    return () => {
      window.clearInterval(id)
      document.removeEventListener("visibilitychange", tick)
    }
  }, [intervalMs])
  return now
}

export function entryEnd(e: Entry, now: number): number {
  return e.end ?? now
}

export function durationMs(e: Entry, now: number): number {
  return Math.max(0, entryEnd(e, now) - e.start)
}

// The readout: 01:07:42.
export function clock(ms: number): string {
  const s = Math.floor(ms / 1000)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = s % 60
  return [h, m, sec].map((n) => String(n).padStart(2, "0")).join(":")
}

// A duration in a list: 1:05.
export function hm(ms: number): string {
  const m = Math.round(ms / MINUTE)
  return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")}`
}

export function hours(ms: number, digits = 1): string {
  return (ms / HOUR).toFixed(digits)
}

// Minutes rounded up to the step; a step of 0 keeps the exact minutes.
export function roundedMinutes(ms: number, step: number): number {
  const minutes = ms / MINUTE
  if (!step) return Math.round(minutes * 100) / 100
  return Math.ceil(minutes / step - 1e-9) * step
}

export function weekDays(anchor: Date): Date[] {
  const start = startOfWeek(anchor, { weekStartsOn })
  return Array.from({ length: 7 }, (_, i) => addDays(start, i))
}

export function monthDays(anchor: Date): Date[] {
  return eachDayOfInterval({ start: startOfMonth(anchor), end: endOfMonth(anchor) })
}

// The part of an entry that falls inside a day, so a timer past midnight counts on both days.
export function msOnDay(e: Entry, day: Date, now: number): number {
  const a = Math.max(e.start, startOfDay(day).getTime())
  const b = Math.min(entryEnd(e, now), endOfDay(day).getTime() + 1)
  return Math.max(0, b - a)
}

export function entriesOnDay(entries: Entry[], day: Date, now: number): Entry[] {
  return entries.filter((e) => msOnDay(e, day, now) > 0).sort((a, b) => b.start - a.start)
}

export function inRange(e: Entry, from: Date, to: Date): boolean {
  return e.end !== null && e.start >= startOfDay(from).getTime() && e.start <= endOfDay(to).getTime()
}

export const timeOfDay = (ms: number) => format(ms, "h:mm a")

export { format, isSameDay }
