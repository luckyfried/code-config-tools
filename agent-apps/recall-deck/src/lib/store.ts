// What the person does stays in this browser under one key: each card's schedule by card id, a count of cards answered per
// day, and their own settings. The deck's starting progress from the inputs fills only what the browser has not set,
// so a rerun with new cards keeps every card that is still there.

import { config, type CardState, type DayLog, type Progress } from "./config.ts"

export const STORAGE_KEY = "recall-deck:progress"

export interface Settings {
  newPerDay: number
  typing: boolean
}

export interface Saved extends Progress {
  settings: Partial<Settings>
}

function isState(v: unknown): v is CardState {
  const s = v as CardState
  return !!s && typeof s.ease === "number" && typeof s.interval === "number" && typeof s.reps === "number"
    && typeof s.due === "string" && /^\d{4}-\d{2}-\d{2}$/.test(s.due)
}

function isLog(v: unknown): v is DayLog {
  const l = v as DayLog
  return !!l && typeof l.seen === "number"
}

/** Reads a saved or exported object, keeping only well-formed entries. */
export function clean(v: unknown): Saved {
  const o = (v && typeof v === "object" ? v : {}) as Partial<Saved>
  const state: Record<string, CardState> = {}
  const log: Record<string, DayLog> = {}
  for (const [id, s] of Object.entries(o.state ?? {})) if (isState(s)) state[id] = s
  for (const [day, l] of Object.entries(o.log ?? {}))
    if (isLog(l)) log[day] = { seen: l.seen, fresh: l.fresh ?? 0, again: l.again ?? 0 }
  const settings: Partial<Settings> = {}
  const s = (o.settings ?? {}) as Partial<Settings>
  if (Number.isInteger(s.newPerDay) && s.newPerDay! > 0) settings.newPerDay = s.newPerDay
  if (typeof s.typing === "boolean") settings.typing = s.typing
  return { state, log, settings }
}

export function readSaved(): Saved | null {
  try {
    const text = localStorage.getItem(STORAGE_KEY)
    return text ? clean(JSON.parse(text)) : null
  } catch {
    return null
  }
}

export function writeSaved(saved: Saved): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
  } catch {
    /* a private window with storage off keeps the session in memory */
  }
}

/** The deck's starting progress, then the browser's on top of it. */
export function initial(saved: Saved | null): Saved {
  const seed = clean(config.progress)
  if (!saved) return seed
  return {
    state: { ...seed.state, ...saved.state },
    log: { ...seed.log, ...saved.log },
    settings: saved.settings,
  }
}

/** An imported file wins for every card and day it carries. */
export function merge(into: Saved, file: Saved): Saved {
  return {
    state: { ...into.state, ...file.state },
    log: { ...into.log, ...file.log },
    settings: { ...into.settings, ...file.settings },
  }
}
