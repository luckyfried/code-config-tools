export type Usual = "breakfast" | "lunch" | "dinner" | "snack"

export type Macros = { calories: number; protein: number; carbs: number; fat: number }

export type Food = Macros & {
  id: string
  name: string
  serving: string
  usual?: Usual
  custom?: boolean
}

export type StartEntry = { daysAgo: number; foodId: string; servings: number; meal: string }

export type AppConfig = {
  name: string
  targets: Macros
  foods: Food[]
  meals: string[]
  water: boolean
  theme: string
  startLog?: StartEntry[]
}

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
  }
}

const fallback: AppConfig = {
  name: "",
  targets: { calories: 2000, protein: 120, carbs: 220, fat: 70 },
  foods: [],
  meals: ["Breakfast", "Lunch", "Dinner", "Snacks"],
  water: false,
  theme: "auto",
}

export function readConfig(): AppConfig {
  const raw = window.__APP_CONFIG__ ?? {}
  return {
    ...fallback,
    ...raw,
    targets: { ...fallback.targets, ...(raw.targets ?? {}) },
    foods: Array.isArray(raw.foods) ? raw.foods : fallback.foods,
    meals: Array.isArray(raw.meals) && raw.meals.length ? raw.meals : fallback.meals,
  }
}

export const MACRO_KEYS = ["protein", "carbs", "fat"] as const
export type MacroKey = (typeof MACRO_KEYS)[number]

export const MACRO_LABEL: Record<MacroKey | "calories", string> = {
  calories: "Calories",
  protein: "Protein",
  carbs: "Carbs",
  fat: "Fat",
}
