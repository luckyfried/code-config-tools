import { useSyncExternalStore } from "react"
import type { Units } from "./config"
import { convert, isSet, setKey, type LiftSet } from "./lift"

/** Every set the person logged, in this browser. The key and shape are the export's too. */
export const LOG_KEY = "lift-log:v1"
const PREFS_KEY = "lift-log:prefs"
const REST_KEY = "lift-log:rest"

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw === null ? fallback : (JSON.parse(raw) as T)
  } catch {
    return fallback
  }
}

function write(key: string, value: unknown) {
  try {
    if (value === null) localStorage.removeItem(key)
    else localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // A full or blocked storage keeps the log in memory for this visit.
  }
}

function createStore<T>(key: string, load: () => T) {
  let value = load()
  const listeners = new Set<() => void>()
  const emit = () => listeners.forEach((l) => l())
  window.addEventListener("storage", (e) => {
    if (e.key !== key) return
    value = load()
    emit()
  })
  return {
    get: () => value,
    /** A value kept for this visit only skips storage. */
    set(next: T, keep = true) {
      value = next
      if (keep) write(key, next)
      emit()
    },
    subscribe(l: () => void) {
      listeners.add(l)
      return () => listeners.delete(l)
    },
  }
}

const loadLog = () => {
  const raw = read<unknown>(LOG_KEY, [])
  return Array.isArray(raw) ? raw.filter(isSet) : []
}
const log = createStore<LiftSet[]>(LOG_KEY, loadLog)

export const useOwnSets = () => useSyncExternalStore(log.subscribe, log.get)
export const ownSets = () => log.get()

export function addSet(s: LiftSet) {
  log.set([...log.get(), s])
}

export function removeSet(target: LiftSet) {
  const key = setKey(target)
  const list = log.get()
  const at = list.findIndex((s) => setKey(s) === key)
  if (at >= 0) log.set([...list.slice(0, at), ...list.slice(at + 1)])
}

export function clearSets() {
  log.set([])
}

/** Adds every set from a file that is not already here; answers how many were new. */
export function importSets(incoming: LiftSet[]) {
  const have = new Set(log.get().map(setKey))
  const fresh = incoming.filter((s) => {
    const k = setKey(s)
    if (have.has(k)) return false
    have.add(k)
    return true
  })
  if (fresh.length) log.set([...log.get(), ...fresh].sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0)))
  return fresh.length
}

export function convertSets(from: Units, to: Units) {
  log.set(log.get().map((s) => ({ ...s, weight: convert(s.weight, from, to) })))
}

export type Prefs = { units?: Units; restSeconds?: number; chime?: boolean }
const prefs = createStore<Prefs>(PREFS_KEY, () => {
  const p = read<Prefs>(PREFS_KEY, {})
  return typeof p === "object" && p !== null ? p : {}
})
export const usePrefs = () => useSyncExternalStore(prefs.subscribe, prefs.get)
export const setPrefs = (patch: Prefs) => prefs.set({ ...prefs.get(), ...patch })

/** A running rest: when it ends and how long it was, kept so a reload mid-rest picks it up. */
export type Rest = { endsAt: number; total: number; quiet?: boolean } | null
const rest = createStore<Rest>(REST_KEY, () => {
  const r = read<Rest>(REST_KEY, null)
  return r && typeof r.endsAt === "number" && typeof r.total === "number" && r.endsAt > Date.now() ? r : null
})
export const useRest = () => useSyncExternalStore(rest.subscribe, rest.get)
/** Starts the rest timer; the sample's rest plays for this visit only and ends without a chime. */
export const startRest = (seconds: number, quiet = false) =>
  rest.set({ endsAt: Date.now() + seconds * 1000, total: seconds, quiet }, !quiet)
export const stopRest = () => rest.set(null)
