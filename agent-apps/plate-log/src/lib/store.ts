import { useCallback, useEffect, useState } from "react"
import type { AppConfig, Food, Macros } from "./config"
import { dayKey, shiftDay, type Entry } from "./nutrition"

/** Everything the page keeps in this browser, under one key. The export is this object as a file. */
export type Saved = {
  days: Record<string, Entry[]>
  foods: Food[]
  water: Record<string, number>
  targets?: Macros
}

export const STORAGE_KEY = "plate-log:data"

let seq = 0
export const newId = () => `${Date.now().toString(36)}${(seq++).toString(36)}${Math.random().toString(36).slice(2, 6)}`

function startFrom(config: AppConfig): Saved {
  const today = dayKey(new Date())
  const days: Record<string, Entry[]> = {}
  const base = Date.now()
  config.startLog?.forEach((s, i) => {
    const key = shiftDay(today, -s.daysAgo)
    ;(days[key] ??= []).push({ id: newId(), foodId: s.foodId, servings: s.servings, meal: s.meal, at: base - (1000 - i) })
  })
  return { days, foods: [], water: config.water && config.startLog?.length ? { [today]: 5 } : {} }
}

function load(config: AppConfig): Saved {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = readSaved(JSON.parse(raw))
      if (parsed) return parsed
    }
  } catch {
    /* A browser that refuses storage starts from the inputs and keeps the day in memory. */
  }
  return startFrom(config)
}

const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v)
const isStr = (v: unknown): v is string => typeof v === "string" && v.length > 0

/** Reads a saved or imported object, keeping every well-formed entry; null when it is not Plate Log's shape. */
export function readSaved(v: unknown): Saved | null {
  if (!v || typeof v !== "object") return null
  const o = v as Record<string, unknown>
  if (!o.days || typeof o.days !== "object") return null
  const days: Record<string, Entry[]> = {}
  for (const [key, list] of Object.entries(o.days as Record<string, unknown>)) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(key) || !Array.isArray(list)) continue
    const entries = list.flatMap((e, i): Entry[] => {
      const x = e as Record<string, unknown>
      if (!x || !isStr(x.foodId) || !isNum(x.servings) || x.servings <= 0 || !isStr(x.meal)) return []
      return [{ id: isStr(x.id) ? x.id : newId(), foodId: x.foodId, servings: x.servings, meal: x.meal, at: isNum(x.at) ? x.at : i }]
    })
    if (entries.length) days[key] = entries
  }
  const foods = Array.isArray(o.foods)
    ? (o.foods as Record<string, unknown>[]).filter(
        (f) => f && isStr(f.id) && isStr(f.name) && isNum(f.calories) && isNum(f.protein) && isNum(f.carbs) && isNum(f.fat),
      ).map((f) => ({ ...(f as unknown as Food), serving: isStr(f.serving) ? f.serving : "1 serving", custom: true }))
    : []
  const water: Record<string, number> = {}
  if (o.water && typeof o.water === "object") {
    for (const [k, n] of Object.entries(o.water as Record<string, unknown>)) if (isNum(n) && n >= 0) water[k] = n
  }
  const t = o.targets as Record<string, unknown> | undefined
  const targets = t && isNum(t.calories) && isNum(t.protein) && isNum(t.carbs) && isNum(t.fat)
    ? { calories: t.calories, protein: t.protein, carbs: t.carbs, fat: t.fat }
    : undefined
  return { days, foods, water, targets }
}

export function useSaved(config: AppConfig) {
  const [saved, setSaved] = useState<Saved>(() => load(config))

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
    } catch {
      /* Storage full or refused: the day stays on screen until the tab closes. */
    }
  }, [saved])

  const add = useCallback((day: string, foodId: string, servings: number, meal: string) => {
    const entry: Entry = { id: newId(), foodId, servings, meal, at: Date.now() }
    setSaved((s) => ({ ...s, days: { ...s.days, [day]: [...(s.days[day] ?? []), entry] } }))
    return entry.id
  }, [])

  const update = useCallback((day: string, id: string, patch: Partial<Pick<Entry, "servings" | "meal">>) => {
    setSaved((s) => ({
      ...s,
      days: { ...s.days, [day]: (s.days[day] ?? []).map((e) => (e.id === id ? { ...e, ...patch } : e)) },
    }))
  }, [])

  const remove = useCallback((day: string, id: string) => {
    setSaved((s) => ({ ...s, days: { ...s.days, [day]: (s.days[day] ?? []).filter((e) => e.id !== id) } }))
  }, [])

  const setWater = useCallback((day: string, n: number) => {
    setSaved((s) => ({ ...s, water: { ...s.water, [day]: Math.max(0, n) } }))
  }, [])

  const addFood = useCallback((food: Food) => {
    setSaved((s) => ({ ...s, foods: [...s.foods, { ...food, custom: true }] }))
  }, [])

  const setTargets = useCallback((targets: Macros | undefined) => {
    setSaved((s) => ({ ...s, targets }))
  }, [])

  const replace = useCallback((next: Saved) => setSaved(next), [])

  return { saved, add, update, remove, setWater, addFood, setTargets, replace }
}

export type Store = ReturnType<typeof useSaved>
