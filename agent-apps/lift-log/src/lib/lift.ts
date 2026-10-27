import { format, parseISO, startOfDay, subDays } from "date-fns"
import type { Equipment, Exercise, Muscle, Units } from "./config"
import { MUSCLES } from "./config"

/** One logged set, as it is kept in localStorage under lift-log:v1. */
export type LiftSet = { date: string; exercise: string; weight: number; reps: number }

/** The Epley estimate of a one-rep max: weight × (1 + reps ÷ 30); a single is its own max. */
export const e1rm = (weight: number, reps: number) => (reps <= 1 ? weight : weight * (1 + reps / 30))

export const round = (n: number, places = 2) => {
  const f = 10 ** places
  return Math.round(n * f) / f
}

/** 102.5, 100, 101.25: never more digits than the plates make. */
export const fmtWeight = (n: number) => String(round(n, 2))

export const fmtE1rm = (n: number) => {
  const r = round(n, 1)
  return Number.isInteger(r) ? r.toLocaleString("en-US") : r.toLocaleString("en-US", { minimumFractionDigits: 1 })
}

export const fmtInt = (n: number) => Math.round(n).toLocaleString("en-US")

export const fmtSets = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1))

export const dayKey = (iso: string) => format(parseISO(iso), "yyyy-MM-dd")

/** The weight steppers move by: two of the smallest plate on a bar, a usual jump otherwise. */
export function weightStep(equipment: Equipment, units: Units, plates: number[]) {
  if (equipment === "barbell") {
    const smallest = plates.length ? Math.min(...plates) : units === "kg" ? 1.25 : 2.5
    return round(smallest * 2, 2)
  }
  if (equipment === "dumbbell") return units === "kg" ? 2 : 5
  return units === "kg" ? 2.5 : 5
}

export function startWeight(equipment: Equipment, units: Units, bar: number) {
  if (equipment === "barbell") return bar
  if (equipment === "bodyweight") return 0
  if (equipment === "dumbbell") return units === "kg" ? 12 : 25
  return units === "kg" ? 30 : 60
}

export type PlateLoad = { perSide: number[]; short: number; belowBar: boolean }

/** What to load on each side of the bar for a total, using the plates the person has (in pairs). */
export function platesFor(total: number, bar: number, plates: number[]): PlateLoad {
  if (total < bar) return { perSide: [], short: 0, belowBar: true }
  let left = round((total - bar) / 2, 4)
  const perSide: number[] = []
  for (const p of [...plates].sort((a, b) => b - a)) {
    while (left + 1e-9 >= p) {
      perSide.push(p)
      left = round(left - p, 4)
    }
  }
  return { perSide, short: round(left * 2, 2), belowBar: false }
}

/** Sets for one exercise, oldest first. */
export const setsOf = (sets: LiftSet[], exercise: string) =>
  sets.filter((s) => s.exercise === exercise).sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0))

export const bestE1rm = (sets: LiftSet[]) => sets.reduce((m, s) => Math.max(m, e1rm(s.weight, s.reps)), 0)

/** Every set that beat the best estimate before it; the first set of a lift is where it starts, not a record. */
export function recordDates(ordered: LiftSet[]) {
  const records = new Set<string>()
  let best = -1
  ordered.forEach((s, i) => {
    const v = e1rm(s.weight, s.reps)
    if (i > 0 && v > best + 1e-9) records.add(s.date)
    best = Math.max(best, v)
  })
  return records
}

export type MuscleWeek = { muscle: Muscle; sets: number; volume: number; level: number }

/** The ramp step a week of sets earns: none, 1 to 3, 4 to 7, 8 to 11, 12 or more. */
export const levelFor = (sets: number) => (sets <= 0 ? 0 : sets < 4 ? 1 : sets < 8 ? 2 : sets < 12 ? 3 : 4)
export const LEVEL_LABEL = ["None", "1–3", "4–7", "8–11", "12+"]

export const weekStart = (now = new Date()) => startOfDay(subDays(now, 6))

/** Sets and volume per muscle over today and the six days before: a full set for the first muscle, half for the rest. */
export function weekByMuscle(sets: LiftSet[], exercises: Map<string, Exercise>, now = new Date()) {
  const from = weekStart(now).toISOString()
  const totals = new Map<Muscle, { sets: number; volume: number }>(MUSCLES.map((m) => [m, { sets: 0, volume: 0 }]))
  let count = 0
  let volume = 0
  const days = new Set<string>()
  for (const s of sets) {
    if (s.date < from) continue
    const ex = exercises.get(s.exercise)
    count += 1
    volume += s.weight * s.reps
    days.add(dayKey(s.date))
    ex?.muscles.forEach((m, i) => {
      const share = i === 0 ? 1 : 0.5
      const t = totals.get(m)!
      t.sets += share
      t.volume += s.weight * s.reps * share
    })
  }
  const muscles: MuscleWeek[] = MUSCLES.map((m) => {
    const t = totals.get(m)!
    return { muscle: m, sets: t.sets, volume: t.volume, level: levelFor(t.sets) }
  })
  return { muscles, sets: count, volume, sessions: days.size }
}

export const KG_PER_LB = 0.45359237

export function convert(weight: number, from: Units, to: Units) {
  if (from === to) return weight
  return round(from === "kg" ? weight / KG_PER_LB : weight * KG_PER_LB, 2)
}

export function isSet(v: unknown): v is LiftSet {
  if (typeof v !== "object" || v === null) return false
  const s = v as Record<string, unknown>
  return (
    typeof s.date === "string" &&
    !Number.isNaN(Date.parse(s.date)) &&
    typeof s.exercise === "string" &&
    s.exercise !== "" &&
    typeof s.weight === "number" &&
    Number.isFinite(s.weight) &&
    s.weight >= 0 &&
    typeof s.reps === "number" &&
    Number.isInteger(s.reps) &&
    s.reps >= 1
  )
}

export const setKey = (s: LiftSet) => `${s.date}|${s.exercise}|${s.weight}|${s.reps}`
