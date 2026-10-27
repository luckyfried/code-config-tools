import { createContext, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { isToday, parseISO } from "date-fns"
import { DEFAULT_BAR, DEFAULT_PLATES, readConfig, type AppConfig, type Exercise, type Muscle, type Units } from "./config"
import {
  bestE1rm,
  e1rm,
  round,
  setsOf,
  startWeight,
  weekByMuscle,
  weightStep,
  type LiftSet,
} from "./lift"
import { sampleLog, SAMPLE_EXERCISE } from "./sample"
import { addSet, startRest, useOwnSets, usePrefs, useRest } from "./store"
import { primeChime } from "./chime"

export type Moment = { key: string; e1rm: number; delay: number }

type Log = {
  config: AppConfig
  units: Units
  plates: number[]
  bar: number
  restSeconds: number
  chimeOn: boolean
  sample: boolean
  sets: LiftSet[]
  exercises: Exercise[]
  exerciseById: Map<string, Exercise>
  selected: Exercise
  select: (id: string) => void
  selectedSets: LiftSet[]
  todaySets: LiftSet[]
  weight: number
  reps: number
  step: number
  stepWeight: (dir: 1 | -1) => void
  stepReps: (dir: 1 | -1) => void
  setWeight: (v: number) => void
  setReps: (v: number) => void
  logSet: () => void
  repeatSet: () => void
  lastOfSelected: LiftSet | undefined
  moment: Moment | null
  flash: { key: string; muscles: Muscle[] } | null
  week: ReturnType<typeof weekByMuscle>
  focus: Muscle | null
  setFocus: (m: Muscle | null) => void
}

const LogContext = createContext<Log | null>(null)

export const useLog = () => {
  const v = useContext(LogContext)
  if (!v) throw new Error("useLog sits inside LogProvider")
  return v
}

const titleFromId = (id: string) => id.replace(/[-_]+/g, " ").replace(/^\w/, (c) => c.toUpperCase())

export function LogProvider({ children }: { children: ReactNode }) {
  const config = useMemo(readConfig, [])
  const prefs = usePrefs()
  const units = prefs.units ?? config.units
  const plates = units === config.units ? config.plates : DEFAULT_PLATES[units]
  const bar = units === config.units ? config.barWeight : DEFAULT_BAR[units]
  const restSeconds = prefs.restSeconds ?? config.restSeconds
  const chimeOn = prefs.chime ?? true

  const own = useOwnSets()
  const sample = own.length === 0
  const sampleSets = useMemo(() => sampleLog(config.exercises, units, bar), [config.exercises, units, bar])
  const sets = sample ? sampleSets : own

  const exerciseById = useMemo(() => {
    const map = new Map(config.exercises.map((e) => [e.id, e]))
    for (const s of sets) {
      if (!map.has(s.exercise)) map.set(s.exercise, { id: s.exercise, label: titleFromId(s.exercise), muscles: [], equipment: "barbell" })
    }
    return map
  }, [config.exercises, sets])
  const exercises = useMemo(() => [...exerciseById.values()], [exerciseById])

  const [selectedId, setSelectedId] = useState(() => {
    if (sample) return exerciseById.has(SAMPLE_EXERCISE) ? SAMPLE_EXERCISE : (sets.at(-1)?.exercise ?? config.exercises[0].id)
    return [...own].sort((a, b) => (a.date < b.date ? -1 : 1)).at(-1)?.exercise ?? config.exercises[0].id
  })
  const selected = exerciseById.get(selectedId) ?? exercises[0]
  const selectedSets = useMemo(() => setsOf(sets, selected.id), [sets, selected.id])
  const lastOfSelected = selectedSets.at(-1)
  const step = weightStep(selected.equipment, units, plates)

  const defaultsFor = useCallback(
    (ex: Exercise, list: LiftSet[]) => {
      const last = setsOf(list, ex.id).at(-1)
      return last ? { weight: last.weight, reps: last.reps } : { weight: startWeight(ex.equipment, units, bar), reps: ex.equipment === "barbell" ? 5 : 10 }
    },
    [units, bar],
  )
  const [draft, setDraft] = useState(() => defaultsFor(selected, sets))

  // The sample opens on the moment its last bench set lands: the plates go on, then the sweep, the chip, and the rest starting.
  const [moment, setMoment] = useState<Moment | null>(() => {
    const last = sample ? setsOf(sets, selectedId).at(-1) : undefined
    return last ? { key: `sample-${last.date}`, e1rm: e1rm(last.weight, last.reps), delay: 800 } : null
  })

  // A unit change converts the log; the stepper follows the converted last set.
  const lastUnits = useRef(units)
  useEffect(() => {
    if (lastUnits.current === units) return
    lastUnits.current = units
    setDraft(defaultsFor(selected, sets))
  }, [units, defaultsFor, selected, sets])

  const select = useCallback(
    (id: string) => {
      const ex = exerciseById.get(id)
      if (!ex) return
      setSelectedId(id)
      setDraft(defaultsFor(ex, sets))
      setMoment(null)
    },
    [exerciseById, defaultsFor, sets],
  )

  const stepWeight = useCallback(
    (dir: 1 | -1) => setDraft((d) => ({ ...d, weight: Math.max(0, Math.min(999, round(d.weight + dir * step, 2))) })),
    [step],
  )
  const stepReps = useCallback((dir: 1 | -1) => setDraft((d) => ({ ...d, reps: Math.max(1, Math.min(100, d.reps + dir)) })), [])
  const setWeight = useCallback((v: number) => setDraft((d) => ({ ...d, weight: Math.max(0, Math.min(999, round(v, 2))) })), [])
  const setReps = useCallback((v: number) => setDraft((d) => ({ ...d, reps: Math.max(1, Math.min(100, Math.round(v))) })), [])

  const [flash, setFlash] = useState<Log["flash"]>(null)
  const rest = useRest()
  const opened = useRef(false)
  useEffect(() => {
    if (opened.current) return
    opened.current = true
    if (sample && !rest) startRest(restSeconds, true)
  }, [sample, rest, restSeconds])

  const log = useCallback(
    (weight: number, reps: number) => {
      primeChime()
      const s: LiftSet = { date: new Date().toISOString(), exercise: selected.id, weight, reps }
      const prior = sample ? [] : setsOf(own, selected.id)
      const v = e1rm(weight, reps)
      const record = prior.length > 0 && v > bestE1rm(prior) + 1e-9
      addSet(s)
      setDraft({ weight, reps })
      setMoment(record ? { key: s.date, e1rm: v, delay: 0 } : null)
      setFlash({ key: s.date, muscles: selected.muscles })
      startRest(restSeconds)
    },
    [selected, sample, own, restSeconds],
  )
  const latest = useRef({ draft, log, lastOfSelected })
  useLayoutEffect(() => {
    latest.current = { draft, log, lastOfSelected }
  })
  const logSet = useCallback(() => latest.current.log(latest.current.draft.weight, latest.current.draft.reps), [])
  const repeatSet = useCallback(() => {
    const last = latest.current.lastOfSelected
    if (last) latest.current.log(last.weight, last.reps)
    else logSet()
  }, [logSet])

  const todaySets = useMemo(() => sets.filter((s) => isToday(parseISO(s.date))), [sets])
  const week = useMemo(() => weekByMuscle(sets, exerciseById), [sets, exerciseById])
  const [focus, setFocus] = useState<Muscle | null>(null)

  const value: Log = {
    config,
    units,
    plates,
    bar,
    restSeconds,
    chimeOn,
    sample,
    sets,
    exercises,
    exerciseById,
    selected,
    select,
    selectedSets,
    todaySets,
    weight: draft.weight,
    reps: draft.reps,
    step,
    stepWeight,
    stepReps,
    setWeight,
    setReps,
    logSet,
    repeatSet,
    lastOfSelected,
    moment,
    flash,
    week,
    focus,
    setFocus,
  }
  return <LogContext.Provider value={value}>{children}</LogContext.Provider>
}
