import { useSyncExternalStore } from "react"
import { config } from "@/config"
import { fitToStages, seedBoard, type Deal } from "@/lib/pipeline"

/** The deals live in this browser under one key, prefixed with the app's name because apps can share an address. */
export const STORAGE_KEY = "deal-board:v1"

interface Saved {
  deals: Deal[]
  savedAt: number
}

function load(): Deal[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const saved = JSON.parse(raw) as Saved
      if (Array.isArray(saved.deals)) return fitToStages(saved.deals, config.stages)
    }
  } catch {
    // A board that cannot be read starts again from the inputs' deals.
  }
  const seeded = seedBoard(config.seedDeals, config.stages, Date.now())
  save(seeded)
  return seeded
}

function save(deals: Deal[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ deals, savedAt: Date.now() } satisfies Saved))
  } catch {
    // Storage can be full or switched off; the board keeps working for this visit.
  }
}

let deals: Deal[] = load()
const listeners = new Set<() => void>()

export function setDeals(next: Deal[] | ((current: Deal[]) => Deal[])) {
  deals = typeof next === "function" ? next(deals) : next
  save(deals)
  for (const listener of listeners) listener()
}

export function updateDeal(id: string, change: (deal: Deal) => Deal) {
  setDeals((current) => current.map((deal) => (deal.id === id ? change(deal) : deal)))
}

export const getDeals = () => deals

export function startOver() {
  setDeals(seedBoard(config.seedDeals, config.stages, Date.now()))
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export const useDeals = () => useSyncExternalStore(subscribe, getDeals)

// Another tab of the same board writes the same key; follow it.
window.addEventListener("storage", (event) => {
  if (event.key !== STORAGE_KEY || event.newValue === null) return
  try {
    deals = fitToStages((JSON.parse(event.newValue) as Saved).deals, config.stages)
    for (const listener of listeners) listener()
  } catch {
    // A half-written value from the other tab is skipped; the next write brings the whole board.
  }
})
