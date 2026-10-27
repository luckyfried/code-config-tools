import sample from "../../inputs.example.json"

export type ItemInput = { name: string; weight?: number }
export type GroupInput = { label: string; items: ItemInput[] }
export type TemplateInput = { id: string; label: string; groups: GroupInput[] }
export type TripInput = { name?: string; templates?: string[]; packed?: string[] }

export type AppConfig = {
  templates: TemplateInput[]
  always: ItemInput[]
  limitKg: number | null
  trip: TripInput
}

declare global {
  interface Window {
    __APP_CONFIG__?: unknown
  }
}

function asItem(value: unknown): ItemInput | null {
  if (typeof value === "string" && value.trim()) return { name: value.trim() }
  if (value && typeof value === "object" && typeof (value as ItemInput).name === "string") {
    const { name, weight } = value as ItemInput
    if (!name.trim()) return null
    return typeof weight === "number" && weight >= 0 ? { name: name.trim(), weight } : { name: name.trim() }
  }
  return null
}

function asTemplate(value: unknown): TemplateInput | null {
  if (!value || typeof value !== "object") return null
  const t = value as TemplateInput
  if (typeof t.id !== "string" || typeof t.label !== "string" || !Array.isArray(t.groups)) return null
  const groups = t.groups
    .filter((g) => g && typeof g.label === "string" && Array.isArray(g.items))
    .map((g) => ({ label: g.label, items: g.items.map(asItem).filter((i): i is ItemInput => i !== null) }))
  return { id: t.id, label: t.label, groups }
}

function normalize(raw: unknown): AppConfig {
  const r = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>
  const templates = Array.isArray(r.templates)
    ? r.templates.map(asTemplate).filter((t): t is TemplateInput => t !== null)
    : []
  const always = Array.isArray(r.always) ? r.always.map(asItem).filter((i): i is ItemInput => i !== null) : []
  const limitKg = typeof r.limitKg === "number" && r.limitKg > 0 ? r.limitKg : null
  const trip = (r.trip && typeof r.trip === "object" ? r.trip : {}) as TripInput
  return { templates, always, limitKg, trip }
}

const fromPage = typeof window !== "undefined" ? window.__APP_CONFIG__ : undefined

/** True when the page was served without a config.js, so it shows the sample. */
export const usingSample = fromPage === undefined

export const config: AppConfig = normalize(fromPage ?? sample)

export const ALWAYS_GROUP = "Every trip"

export type Item = {
  key: string
  name: string
  weight: number | null
  group: string
  added: boolean
}

export type Group = { label: string; items: Item[] }

export const keyOf = (name: string) => name.trim().toLowerCase().replace(/\s+/g, " ")

export type AddedItem = { name: string; group: string; weight: number | null }

/**
 * The list for a set of templates: the always items first, then each template's groups merged by label in the
 * order they first appear; an item already on the list by name is not listed twice. Added items join their group.
 */
export function composeList(templateIds: string[], added: AddedItem[]): Group[] {
  const groups = new Map<string, Group>()
  const seen = new Set<string>()
  const put = (groupLabel: string, item: ItemInput | AddedItem, isAdded: boolean) => {
    const key = keyOf(item.name)
    if (seen.has(key)) return
    seen.add(key)
    const gk = keyOf(groupLabel)
    let group = groups.get(gk)
    if (!group) {
      group = { label: groupLabel, items: [] }
      groups.set(gk, group)
    }
    const weight = typeof item.weight === "number" ? item.weight : null
    group.items.push({ key, name: item.name, weight, group: group.label, added: isAdded })
  }
  for (const item of config.always) put(ALWAYS_GROUP, item, false)
  for (const id of templateIds) {
    const template = config.templates.find((t) => t.id === id)
    if (!template) continue
    for (const group of template.groups) for (const item of group.items) put(group.label, item, false)
  }
  for (const item of added) put(item.group || ALWAYS_GROUP, item, true)
  return [...groups.values()].filter((g) => g.items.length > 0)
}

/** How many items each chosen template brings that the ones before it did not. */
export function addedCounts(templateIds: string[]): Map<string, number> {
  const seen = new Set(config.always.map((i) => keyOf(i.name)))
  const counts = new Map<string, number>()
  for (const id of templateIds) {
    const template = config.templates.find((t) => t.id === id)
    if (!template) continue
    let n = 0
    for (const group of template.groups)
      for (const item of group.items) {
        const key = keyOf(item.name)
        if (!seen.has(key)) {
          seen.add(key)
          n++
        }
      }
    counts.set(id, n)
  }
  return counts
}

export function templateSize(id: string): number {
  const template = config.templates.find((t) => t.id === id)
  if (!template) return 0
  return new Set(template.groups.flatMap((g) => g.items.map((i) => keyOf(i.name)))).size
}
