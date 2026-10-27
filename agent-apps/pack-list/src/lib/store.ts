import { config, keyOf, type AddedItem } from "./config"

export const STORAGE_KEY = "pack-list:v1"

export type TripState = {
  name: string
  templates: string[]
  packed: string[]
  added: AddedItem[]
}

function firstTrip(): TripState {
  const ids = new Set(config.templates.map((t) => t.id))
  const chosen = (config.trip.templates ?? []).filter((id) => ids.has(id))
  const templates = chosen.length > 0 ? chosen : config.templates.slice(0, 1).map((t) => t.id)
  const label = config.templates.find((t) => t.id === templates[0])?.label
  return {
    name: config.trip.name?.trim() || label || "My trip",
    templates,
    packed: [],
    added: [],
  }
}

/** The items the inputs say are already in the bag, checked one by one on the very first visit. */
export const firstPacked = (config.trip.packed ?? []).map(keyOf)

export function parseTrip(value: unknown): TripState | null {
  if (!value || typeof value !== "object") return null
  const v = value as Partial<TripState>
  if (typeof v.name !== "string" || !Array.isArray(v.templates) || !Array.isArray(v.packed)) return null
  const added = Array.isArray(v.added)
    ? v.added
        .filter((a) => a && typeof a.name === "string" && a.name.trim())
        .map((a) => ({
          name: a.name.trim(),
          group: typeof a.group === "string" ? a.group : "",
          weight: typeof a.weight === "number" ? a.weight : null,
        }))
    : []
  return {
    name: v.name,
    templates: v.templates.filter((t): t is string => typeof t === "string"),
    packed: v.packed.filter((p): p is string => typeof p === "string"),
    added,
  }
}

export function loadTrip(): { trip: TripState; fresh: boolean } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const trip = parseTrip(JSON.parse(raw))
      if (trip) return { trip, fresh: false }
    }
  } catch {
    // A blocked or corrupt store starts a fresh trip.
  }
  return { trip: firstTrip(), fresh: true }
}

export function saveTrip(trip: TripState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trip))
  } catch {
    // Private windows can refuse storage; the list still works for this visit.
  }
}

export function exportTrip(trip: TripState) {
  const blob = new Blob([JSON.stringify({ app: "pack-list", ...trip }, null, 2)], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  const slug = trip.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "trip"
  a.href = url
  a.download = `pack-list-${slug}.json`
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
