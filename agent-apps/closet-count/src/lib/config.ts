import { CATEGORIES, SEASONS, type Category, type Season } from "./types"

export interface ItemInput {
  id: string
  name: string
  category: Category
  color: string
  price?: number | null
  brand?: string
  seasons?: Season[]
  wears?: number
  lastWorn?: string
}

export interface OutfitInput {
  id: string
  name: string
  items: Record<string, string | null>
  wears?: number
  lastWorn?: string
}

export interface AppConfig {
  name: string
  currency: string
  items: ItemInput[]
  outfits: OutfitInput[]
  slots: string[]
  dustyDays: number
  capsuleSize: number
  theme: string
  copy: Record<string, string>
}

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
    __APP_COPY__?: Record<string, string>
  }
}

const HEX = /^#[0-9a-fA-F]{6}$/

function readConfig(): AppConfig {
  const raw = window.__APP_CONFIG__ ?? {}
  const items = (Array.isArray(raw.items) ? raw.items : []).filter(
    (i): i is ItemInput =>
      !!i && typeof i.id === "string" && typeof i.name === "string" && CATEGORIES.includes(i.category) && HEX.test(i.color),
  )
  return {
    name: typeof raw.name === "string" && raw.name.trim() ? raw.name : "My closet",
    currency: typeof raw.currency === "string" && raw.currency.length === 3 ? raw.currency.toUpperCase() : "USD",
    items: items.map((i) => ({ ...i, seasons: (i.seasons ?? []).filter((s) => SEASONS.includes(s)) })),
    outfits: Array.isArray(raw.outfits) ? raw.outfits.filter((o) => o && typeof o.id === "string" && o.items) : [],
    slots: Array.isArray(raw.slots) && raw.slots.length ? raw.slots : ["top", "bottom", "shoes", "layer"],
    dustyDays: typeof raw.dustyDays === "number" && raw.dustyDays > 0 ? raw.dustyDays : 90,
    capsuleSize: typeof raw.capsuleSize === "number" && raw.capsuleSize > 0 ? raw.capsuleSize : 33,
    theme: typeof raw.theme === "string" ? raw.theme : "auto",
    copy: raw.copy && typeof raw.copy === "object" ? raw.copy : {},
  }
}

export const config: AppConfig = readConfig()

const copy: Record<string, string> = { ...(window.__APP_COPY__ ?? {}), ...config.copy }

/** The words on the page, by key, with `{n}`-style holes filled from `vars`. */
export function t(key: string, vars: Record<string, string | number> = {}): string {
  const text = copy[key] ?? key
  return text.replace(/\{(\w+)\}/g, (_, k: string) => String(vars[k] ?? ""))
}

/** Which categories an outfit slot takes: a top slot also takes a dress. */
export function slotCategories(slot: string): Category[] {
  if (slot === "top") return ["top", "dress"]
  return CATEGORIES.includes(slot as Category) ? [slot as Category] : []
}
