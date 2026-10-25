import { addDays, format } from "date-fns"
import type { Food, Macros, MacroKey, Usual } from "./config"

export type Entry = { id: string; foodId: string; servings: number; meal: string; at: number }

export const dayKey = (d: Date) => format(d, "yyyy-MM-dd")

export const parseDay = (key: string) => {
  const [y, m, d] = key.split("-").map(Number)
  return new Date(y, m - 1, d)
}

export const shiftDay = (key: string, days: number) => dayKey(addDays(parseDay(key), days))

export const zero = (): Macros => ({ calories: 0, protein: 0, carbs: 0, fat: 0 })

export function totals(entries: Entry[], foods: Map<string, Food>): Macros {
  const t = zero()
  for (const e of entries) {
    const f = foods.get(e.foodId)
    if (!f) continue
    t.calories += f.calories * e.servings
    t.protein += f.protein * e.servings
    t.carbs += f.carbs * e.servings
    t.fat += f.fat * e.servings
  }
  return t
}

/** The macro that brings the most calories to a food: 4 kcal per gram of protein or carbs, 9 per gram of fat. */
export function leadMacro(f: Macros): MacroKey {
  const p = f.protein * 4
  const c = f.carbs * 4
  const fa = f.fat * 9
  if (p >= c && p >= fa) return "protein"
  return c >= fa ? "carbs" : "fat"
}

/** The part of the day it is now, the way people eat. */
export function periodAt(d: Date): Usual {
  const h = d.getHours() + d.getMinutes() / 60
  if (h >= 4.5 && h < 10.5) return "breakfast"
  if (h >= 10.5 && h < 15) return "lunch"
  if (h >= 15 && h < 17.5) return "snack"
  if (h >= 17.5 && h < 21.5) return "dinner"
  return "snack"
}

const ROTATION: Record<Usual, Usual[]> = {
  breakfast: ["breakfast", "snack", "lunch", "dinner"],
  lunch: ["lunch", "snack", "dinner", "breakfast"],
  snack: ["snack", "dinner", "lunch", "breakfast"],
  dinner: ["dinner", "snack", "breakfast", "lunch"],
}

/** The tray order: foods usually eaten now first, then what comes next, each group by how often it is logged. */
export function trayOrder(foods: Food[], now: Date, counts: Map<string, number>): Food[] {
  const rank = ROTATION[periodAt(now)]
  const r = (f: Food) => (f.usual ? rank.indexOf(f.usual) : rank.length)
  return foods.toSorted(
    (a, b) => r(a) - r(b) || (counts.get(b.id) ?? 0) - (counts.get(a.id) ?? 0) || a.name.localeCompare(b.name),
  )
}

/** The meal a food logged now goes under: the meal named like the part of the day, else by position. */
export function mealAt(meals: string[], now: Date): string {
  const p = periodAt(now)
  const named = meals.find((m) => m.toLowerCase().startsWith(p.slice(0, 4)))
  if (named) return named
  const order: Usual[] = ["breakfast", "lunch", "snack", "dinner"]
  const i = Math.min(meals.length - 1, Math.floor((order.indexOf(p) / order.length) * meals.length))
  return meals[i]
}

const FRACTIONS: Record<number, string> = { 0.25: "¼", 0.5: "½", 0.75: "¾" }

export function servingsText(n: number) {
  const whole = Math.floor(n)
  const part = FRACTIONS[Math.round((n - whole) * 100) / 100] ?? ""
  if (!part) return String(whole)
  return whole ? `${whole}${part}` : part
}

export const fmt = (n: number) => Math.round(n).toLocaleString("en-US")

/** A day counts toward the streak when its calories land within a tenth of the target, over or under. */
export const withinTarget = (calories: number, target: number) =>
  calories > 0 && Math.abs(calories - target) <= target * 0.1
