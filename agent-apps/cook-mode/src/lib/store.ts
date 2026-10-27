import { useSyncExternalStore } from "react"
import { config } from "./config"

/** Every key starts with the app's slug, since apps hosted at one address share one origin. */
const PREFIX = "cook-mode:"

export interface Store<T> {
  get: () => T
  set: (next: T | ((current: T) => T)) => void
  subscribe: (listener: () => void) => () => void
}

export function createStore<T>(name: string, initial: T): Store<T> {
  const key = PREFIX + name
  let value = initial
  try {
    const saved = localStorage.getItem(key)
    if (saved !== null) value = JSON.parse(saved) as T
  } catch {
    // Storage that cannot be read starts fresh.
  }
  const listeners = new Set<() => void>()
  return {
    get: () => value,
    set(next) {
      value = typeof next === "function" ? (next as (current: T) => T)(value) : next
      try {
        localStorage.setItem(key, JSON.stringify(value))
      } catch {
        // A full or blocked storage keeps the value for this visit only.
      }
      listeners.forEach((listener) => listener())
    },
    subscribe(listener) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}

export function useStore<T>(store: Store<T>) {
  return useSyncExternalStore(store.subscribe, store.get, store.get)
}

/** The recipes marked for this week; tonight's is on the list until it is taken off. */
export const weekStore = createStore<string[]>("week", config.pinned ? [config.pinned] : [])
/** Servings chosen per recipe. */
export const servingsStore = createStore<Record<string, number>>("servings", {})
/** Ingredients already in the kitchen, as "recipe:index"; every other one goes on the list. */
export const haveStore = createStore<string[]>("have", [])
/** Shopping lines picked up at the store. */
export const gotStore = createStore<string[]>("got", [])

export function servingsFor(id: string, base: number, chosen: Record<string, number>) {
  return chosen[id] ?? base
}

export function toggleIn(list: string[], item: string) {
  return list.includes(item) ? list.filter((entry) => entry !== item) : [...list, item]
}
