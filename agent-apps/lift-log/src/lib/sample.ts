import { setHours, setMinutes, startOfDay, subDays } from "date-fns"
import type { Exercise, Units } from "./config"
import { round, startWeight, type LiftSet } from "./lift"

/**
 * Six weeks of a four-day upper and lower split, ending with today's bench press: the page shows this
 * until the person logs a set of their own. Weights are in kilograms and climb a little each week, with
 * one flat week, the way a real log does.
 */
type Slot = { id: string; start: number; perWeek: number; sets: [number, number][]; main?: boolean }

const A: Slot[] = [
  { id: "bench-press", main: true, start: 85, perWeek: 2.5, sets: [[0.7, 8], [0.85, 5], [0.95, 5], [1, 5]] },
  { id: "barbell-row", start: 62.5, perWeek: 2.5, sets: [[1, 8], [1, 8], [1, 8]] },
  { id: "overhead-press", main: true, start: 45, perWeek: 1.25, sets: [[1, 6], [1, 6], [1, 6]] },
  { id: "barbell-curl", start: 30, perWeek: 1.25, sets: [[1, 10], [1, 10]] },
]
const B: Slot[] = [
  { id: "back-squat", main: true, start: 105, perWeek: 2.5, sets: [[0.75, 5], [1, 5], [1, 5], [1, 5]] },
  { id: "romanian-deadlift", start: 90, perWeek: 2.5, sets: [[1, 8], [1, 8], [1, 8]] },
  { id: "leg-curl", start: 40, perWeek: 2.5, sets: [[1, 12], [1, 12]] },
  { id: "calf-raise", start: 80, perWeek: 5, sets: [[1, 12], [1, 12], [1, 12]] },
]
const C: Slot[] = [
  { id: "incline-bench", start: 65, perWeek: 2.5, sets: [[1, 8], [1, 8], [1, 8]] },
  { id: "pull-up", start: 5, perWeek: 2.5, sets: [[1, 8], [1, 7], [1, 6], [1, 6]] },
  { id: "lateral-raise", start: 10, perWeek: 0.5, sets: [[1, 15], [1, 15], [1, 15]] },
  { id: "triceps-pushdown", start: 30, perWeek: 2.5, sets: [[1, 12], [1, 12], [1, 12]] },
]
const D: Slot[] = [
  { id: "deadlift", main: true, start: 140, perWeek: 5, sets: [[0.8, 5], [1, 5], [1, 3]] },
  { id: "hip-thrust", start: 100, perWeek: 5, sets: [[1, 10], [1, 10], [1, 10]] },
  { id: "leg-press", start: 160, perWeek: 10, sets: [[1, 10], [1, 10]] },
  { id: "hanging-leg-raise", start: 0, perWeek: 0, sets: [[1, 12], [1, 12], [1, 12]] },
]

/** Days before today for each session, newest first: A today, then D, C, B, and so on back six weeks. */
const SESSIONS: { daysAgo: number; slots: Slot[] }[] = []
for (let week = 0; week < 6; week++) {
  SESSIONS.push({ daysAgo: week * 7, slots: A }, { daysAgo: week * 7 + 2, slots: D }, { daysAgo: week * 7 + 4, slots: C })
  SESSIONS.push({ daysAgo: week * 7 + 5, slots: B })
}

const FLAT_WEEK = 2

const snap = (kg: number, step: number) => round(Math.round(kg / step) * step, 2)

export function sampleLog(exercises: Exercise[], units: Units, bar: number, now = new Date()): LiftSet[] {
  const known = new Map(exercises.map((e) => [e.id, e]))
  const out: LiftSet[] = []
  const toUnits = (kg: number) => (units === "kg" ? snap(kg, 2.5) : snap(kg * 2.20462, 5))
  const matched = [...A, ...B, ...C, ...D].filter((s) => known.has(s.id)).length
  const slotsFor = (slots: Slot[], i: number): Slot[] =>
    matched >= 4
      ? slots.filter((s) => known.has(s.id))
      : exercises.slice((i % 3) * 3, (i % 3) * 3 + 3).map((e) => ({
          id: e.id,
          start: units === "kg" ? Math.max(startWeight(e.equipment, units, bar), 20) : startWeight(e.equipment, units, bar) / 2.2,
          perWeek: e.equipment === "bodyweight" ? 0 : 2.5,
          sets: [[1, 8], [1, 8], [1, 8]],
        }))

  SESSIONS.forEach(({ daysAgo, slots }, i) => {
    const week = Math.floor(daysAgo / 7)
    const climbed = 5 - week - (week < FLAT_WEEK ? 1 : 0)
    const today = daysAgo === 0
    // Today's session is under way: the bench press is done and its last set is the record.
    const list = today ? slotsFor(slots, i).slice(0, 1) : slotsFor(slots, i)
    const total = list.reduce((n, s) => n + s.sets.length, 0)
    let at = today ? new Date(now.getTime() - total * 3.5 * 60_000) : setMinutes(setHours(startOfDay(subDays(now, daysAgo)), 18), 5)
    for (const slot of list) {
      // The main lifts climb every week; the rest every other week.
      const steps = slot.main ? Math.max(climbed, 0) : Math.floor(Math.max(climbed, 0) / 2)
      const top = slot.start + slot.perWeek * steps + (today && slot.id === "bench-press" ? 2.5 : 0)
      for (const [share, reps] of slot.sets) {
        at = new Date(at.getTime() + 3.5 * 60_000)
        out.push({ date: at.toISOString(), exercise: slot.id, weight: toUnits(top * share), reps })
      }
    }
  })
  return out.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0))
}

/** The sample's last bench set is a record, so the page opens on the moment one lands. */
export const SAMPLE_EXERCISE = "bench-press"
