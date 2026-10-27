import { useSyncExternalStore } from "react"
import { config, type ItemInput, type OutfitInput } from "./config"
import { daysSince, seasonOf, today } from "./dates"
import { CATEGORIES, SEASONS, type Closet, type Item, type Outfit, type Season } from "./types"

/** Everything the person enters or taps lives in this one localStorage key. */
export const STORAGE_KEY = "closet-count"

function itemFromInput(i: ItemInput, day: string): Item {
  const wears = typeof i.wears === "number" && i.wears >= 0 ? Math.round(i.wears) : 0
  return {
    id: i.id,
    name: i.name,
    category: i.category,
    color: i.color.toLowerCase(),
    price: typeof i.price === "number" && i.price >= 0 ? i.price : null,
    brand: i.brand ?? "",
    seasons: i.seasons ?? [],
    wears: i.lastWorn ? Math.max(wears, 1) : wears,
    worn: i.lastWorn ? [i.lastWorn] : [],
    since: i.lastWorn && i.lastWorn < day ? i.lastWorn : day,
    keptOn: null,
  }
}

function outfitFromInput(o: OutfitInput, ids: Set<string>): Outfit {
  const items: Record<string, string | null> = {}
  for (const slot of config.slots) {
    const id = o.items[slot]
    items[slot] = id && ids.has(id) ? id : null
  }
  return {
    id: o.id,
    name: o.name,
    items,
    wears: typeof o.wears === "number" && o.wears >= 0 ? Math.round(o.wears) : 0,
    worn: o.lastWorn ? [o.lastWorn] : [],
  }
}

function emptyCloset(): Closet {
  return { items: [], outfits: [], given: [], capsule: {}, currency: config.currency, seededItems: [], seededOutfits: [] }
}

/** Brings in whatever the starting closet holds that this browser has not seen yet; running it twice changes nothing. */
function seed(c: Closet): Closet {
  const day = today()
  const seenItems = new Set(c.seededItems)
  const fresh = config.items.filter((i) => !seenItems.has(i.id))
  const items = [...c.items, ...fresh.map((i) => itemFromInput(i, day))]
  const ids = new Set(items.map((i) => i.id))
  const seenOutfits = new Set(c.seededOutfits)
  const freshOutfits = config.outfits.filter((o) => !seenOutfits.has(o.id))
  if (!fresh.length && !freshOutfits.length) return c
  return {
    ...c,
    items,
    outfits: [...c.outfits, ...freshOutfits.map((o) => outfitFromInput(o, ids))],
    seededItems: [...c.seededItems, ...fresh.map((i) => i.id)],
    seededOutfits: [...c.seededOutfits, ...freshOutfits.map((o) => o.id)],
  }
}

/** A closet read from storage or an import, with anything malformed dropped rather than trusted. */
export function parseCloset(value: unknown): Closet | null {
  if (!value || typeof value !== "object") return null
  const v = value as Partial<Closet>
  if (!Array.isArray(v.items) || !Array.isArray(v.outfits)) return null
  const items = v.items.filter(
    (i): i is Item =>
      !!i && typeof i.id === "string" && typeof i.name === "string" && CATEGORIES.includes(i.category) &&
      typeof i.color === "string" && typeof i.wears === "number" && Array.isArray(i.worn),
  )
  const outfits = v.outfits.filter((o): o is Outfit => !!o && typeof o.id === "string" && !!o.items && Array.isArray(o.worn))
  return {
    items: items.map((i) => ({ ...i, seasons: (i.seasons ?? []).filter((s) => SEASONS.includes(s)), since: i.since ?? today(), keptOn: i.keptOn ?? null, brand: i.brand ?? "", price: i.price ?? null })),
    outfits: outfits.map((o) => ({ ...o, wears: typeof o.wears === "number" ? o.wears : 0 })),
    given: Array.isArray(v.given) ? v.given : [],
    capsule: v.capsule && typeof v.capsule === "object" ? v.capsule : {},
    currency: typeof v.currency === "string" ? v.currency : config.currency,
    seededItems: Array.isArray(v.seededItems) ? v.seededItems : items.map((i) => i.id),
    seededOutfits: Array.isArray(v.seededOutfits) ? v.seededOutfits : outfits.map((o) => o.id),
  }
}

function load(): Closet {
  try {
    const stored = parseCloset(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null"))
    return seed(stored ?? emptyCloset())
  } catch {
    return seed(emptyCloset())
  }
}

let state: Closet = load()
const listeners = new Set<() => void>()

function commit(next: Closet) {
  state = next
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    /* A full or blocked storage keeps the change for this visit only. */
  }
  listeners.forEach((l) => l())
}
commit(state)

export function useCloset(): Closet {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l)
      return () => listeners.delete(l)
    },
    () => state,
  )
}

export function getCloset(): Closet {
  return state
}

const lastOf = (days: string[]) => (days.length ? days[days.length - 1] : null)

export function lastWorn(item: Pick<Item, "worn">): string | null {
  return lastOf(item.worn)
}

export function wornToday(x: { worn: string[] }): boolean {
  return x.worn.includes(today())
}

/** Days on the Dusty clock: since the last wear, the last Keep, or the day it joined, whichever is latest. */
export function idleDays(item: Item): number {
  const marks = [lastOf(item.worn), item.keptOn, item.since].filter((d): d is string => !!d).sort()
  return daysSince(marks[marks.length - 1])
}

export function isDusty(item: Item): boolean {
  return idleDays(item) > config.dustyDays
}

/** From 0 at the threshold to 1 six weeks past it: how far the color has faded. */
export function dustLevel(item: Item): number {
  const past = idleDays(item) - config.dustyDays
  return past <= 0 ? 0 : Math.min(1, past / 42)
}

function setItem(id: string, change: (i: Item) => Item) {
  commit({ ...state, items: state.items.map((i) => (i.id === id ? change(i) : i)) })
}

function mark(i: Item, day: string): Item {
  return i.worn.includes(day) ? i : { ...i, wears: i.wears + 1, worn: [...i.worn, day].sort() }
}

function unmark(i: Item, day: string): Item {
  return i.worn.includes(day) ? { ...i, wears: Math.max(0, i.wears - 1), worn: i.worn.filter((d) => d !== day) } : i
}

/** One tap a day: marks the item worn today, or takes back today's mark. */
export function toggleItemWorn(id: string) {
  const day = today()
  setItem(id, (i) => (i.worn.includes(day) ? unmark(i, day) : mark(i, day)))
}

/** Marks an outfit and every item in it worn today, or takes the whole day back. */
export function toggleOutfitWorn(id: string) {
  const day = today()
  const outfit = state.outfits.find((o) => o.id === id)
  if (!outfit) return
  const on = !outfit.worn.includes(day)
  const ids = new Set(Object.values(outfit.items).filter((v): v is string => !!v))
  commit({
    ...state,
    outfits: state.outfits.map((o) =>
      o.id !== id ? o : on ? { ...o, wears: o.wears + 1, worn: [...o.worn, day] } : { ...o, wears: Math.max(0, o.wears - 1), worn: o.worn.filter((d) => d !== day) },
    ),
    items: state.items.map((i) => (ids.has(i.id) ? (on ? mark(i, day) : unmark(i, day)) : i)),
  })
}

export function keepItem(id: string) {
  setItem(id, (i) => ({ ...i, keptOn: today() }))
}

export function giveAway(id: string) {
  const item = state.items.find((i) => i.id === id)
  if (!item) return
  const capsule: Closet["capsule"] = {}
  for (const s of SEASONS) {
    const list = state.capsule[s]
    if (list) capsule[s] = list.filter((x) => x !== id)
  }
  commit({
    ...state,
    items: state.items.filter((i) => i.id !== id),
    outfits: state.outfits.map((o) => ({
      ...o,
      items: Object.fromEntries(Object.entries(o.items).map(([slot, v]) => [slot, v === id ? null : v])),
    })),
    given: [...state.given, { id, name: item.name, on: today() }],
    capsule,
  })
}

function slug(text: string, taken: Set<string>): string {
  const base = text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "item"
  let id = base
  for (let n = 2; taken.has(id); n++) id = `${base}-${n}`
  return id
}

export type ItemDraft = Pick<Item, "name" | "category" | "color" | "price" | "brand" | "seasons">

export function addItem(draft: ItemDraft): string {
  const id = slug(draft.name, new Set([...state.items.map((i) => i.id), ...state.given.map((g) => g.id)]))
  const item: Item = { ...draft, id, wears: 0, worn: [], since: today(), keptOn: null }
  commit({ ...state, items: [...state.items, item] })
  return id
}

export function editItem(id: string, draft: ItemDraft) {
  setItem(id, (i) => ({ ...i, ...draft }))
}

export function saveOutfit(draft: { id?: string; name: string; items: Record<string, string | null> }): string {
  if (draft.id && state.outfits.some((o) => o.id === draft.id)) {
    commit({ ...state, outfits: state.outfits.map((o) => (o.id === draft.id ? { ...o, name: draft.name, items: draft.items } : o)) })
    return draft.id
  }
  const id = slug(draft.name, new Set(state.outfits.map((o) => o.id)))
  commit({ ...state, outfits: [...state.outfits, { id, name: draft.name, items: draft.items, wears: 0, worn: [] }] })
  return id
}

export function removeOutfit(id: string) {
  commit({ ...state, outfits: state.outfits.filter((o) => o.id !== id) })
}

export const currentSeason = (): Season => seasonOf(today())

export function capsuleIds(c: Closet, season: Season): string[] {
  const ids = new Set(c.items.map((i) => i.id))
  return (c.capsule[season] ?? c.items.filter((i) => i.seasons.includes(season)).map((i) => i.id)).filter((id) => ids.has(id))
}

export function toggleCapsule(season: Season, id: string) {
  const list = capsuleIds(state, season)
  const next = list.includes(id) ? list.filter((x) => x !== id) : [...list, id]
  commit({ ...state, capsule: { ...state.capsule, [season]: next } })
}

export function setCurrency(currency: string) {
  commit({ ...state, currency })
}

export function exportCloset(): string {
  return JSON.stringify({ app: "closet-count", exported: today(), ...state }, null, 2)
}

/** Replaces the closet with an exported one; returns false when the file is not a Closet Count export. */
export function importCloset(text: string): boolean {
  try {
    const parsed = parseCloset(JSON.parse(text))
    if (!parsed) return false
    commit(parsed)
    return true
  } catch {
    return false
  }
}

/** Goes back to the starting closet the agent wrote, dropping every tap and edit made in this browser. */
export function startOver() {
  commit(seed(emptyCloset()))
}
