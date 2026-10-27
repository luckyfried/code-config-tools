import { useSyncExternalStore } from "react"
import { config } from "./config"
import { sampleEntries } from "./sample"

// Everything the person does lives in localStorage under one key. An entry whose end is null is the running timer;
// there is at most one. Times are epoch milliseconds, so a sleeping laptop or a throttled tab changes nothing.
export type Entry = { id: string; start: number; end: number | null; clientId: string; note: string }
export type Ledger = { entries: Entry[]; rounding: number | null; lastClientId: string | null }

export const STORAGE_KEY = "hours-ledger"

const empty: Ledger = { entries: [], rounding: null, lastClientId: null }

function load(): Ledger {
  try {
    const text = localStorage.getItem(STORAGE_KEY)
    if (text) return { ...empty, ...(JSON.parse(text) as Ledger) }
  } catch {
    // A value that does not parse is replaced by a fresh ledger below.
  }
  const fresh: Ledger = config.sample ? { ...empty, entries: sampleEntries(Date.now()) } : { ...empty }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(fresh))
  return fresh
}

let state: Ledger = load()

// The entry a switch of client just finished, so the day's list can drop it in from the timer card.
let dropped: { id: string; at: number } | null = null
export function justDropped(id: string): boolean {
  return dropped !== null && dropped.id === id && Date.now() - dropped.at < 1500
}
const listeners = new Set<() => void>()

function commit(next: Ledger) {
  state = next
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  listeners.forEach((l) => l())
}

window.addEventListener("storage", (e) => {
  if (e.key === STORAGE_KEY) {
    state = load()
    listeners.forEach((l) => l())
  }
})

function subscribe(l: () => void) {
  listeners.add(l)
  return () => listeners.delete(l)
}

export function useLedger(): Ledger {
  return useSyncExternalStore(subscribe, () => state)
}

export function newId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8)
}

export function running(l: Ledger): Entry | undefined {
  return l.entries.find((e) => e.end === null)
}

export function effectiveRounding(l: Ledger): number {
  return l.rounding ?? config.rounding
}

// Starts a timer for the client; a timer already running ends now and becomes a finished entry.
// Returns the id of the entry that just finished, if any.
export function startTimer(clientId: string, note = ""): string | null {
  const now = Date.now()
  const current = running(state)
  const entries = state.entries.map((e) => (e.end === null ? { ...e, end: now } : e))
  entries.push({ id: newId(), start: now, end: null, clientId, note })
  dropped = current ? { id: current.id, at: now } : null
  commit({ ...state, entries, lastClientId: clientId })
  return current ? current.id : null
}

export function stopTimer(at = Date.now()): string | null {
  const current = running(state)
  if (!current) return null
  commit({ ...state, entries: state.entries.map((e) => (e.id === current.id ? { ...e, end: Math.max(at, e.start + 1000) } : e)) })
  return current.id
}

export function updateEntry(id: string, patch: Partial<Omit<Entry, "id">>) {
  commit({ ...state, entries: state.entries.map((e) => (e.id === id ? { ...e, ...patch } : e)) })
}

export function addEntry(entry: Omit<Entry, "id">) {
  commit({ ...state, entries: [...state.entries, { ...entry, id: newId() }], lastClientId: entry.clientId })
}

export function deleteEntry(id: string) {
  commit({ ...state, entries: state.entries.filter((e) => e.id !== id) })
}

export function setRounding(rounding: number) {
  commit({ ...state, rounding })
}

export function clearEntries() {
  commit({ ...state, entries: [] })
}

// Merges entries from an export by id, so importing the same file twice adds nothing the second time.
export function importEntries(incoming: Entry[]): number {
  const known = new Set(state.entries.map((e) => e.id))
  const added = incoming.filter((e) => !known.has(e.id))
  const kept = running(state) ? added.filter((e) => e.end !== null) : added
  commit({ ...state, entries: [...state.entries, ...kept] })
  return kept.length
}
