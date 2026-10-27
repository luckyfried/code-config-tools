export type Units = "metric" | "us"

export interface Ingredient {
  amount: number | null
  unit: string
  name: string
  /** The step (counted from 1) whose strip pins this ingredient. */
  step?: number
}

export interface Recipe {
  id: string
  title: string
  servings: number
  minutes: number
  cuisine: string
  tags: string[]
  ingredients: Ingredient[]
  steps: string[]
  image?: string
}

export interface AppConfig {
  kitchen: string
  units: Units
  theme: string
  pinned: string
  tags: string[]
  recipes: Recipe[]
}

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
  }
}

function readConfig(): AppConfig {
  const raw = (typeof window !== "undefined" && window.__APP_CONFIG__) || {}
  const recipes = Array.isArray(raw.recipes) ? raw.recipes : []
  return {
    kitchen: raw.kitchen || "My kitchen",
    units: raw.units === "metric" ? "metric" : "us",
    theme: raw.theme || "auto",
    pinned: raw.pinned || recipes[0]?.id || "",
    tags: Array.isArray(raw.tags) ? raw.tags : [],
    recipes: recipes.map((recipe) => ({
      ...recipe,
      tags: recipe.tags ?? [],
      ingredients: recipe.ingredients ?? [],
      steps: recipe.steps ?? [],
    })),
  }
}

export const config = readConfig()

export const recipeById = new Map(config.recipes.map((recipe) => [recipe.id, recipe]))

/** The step's own ingredients, in the order the recipe lists them. */
export function ingredientsForStep(recipe: Recipe, stepIndex: number) {
  return recipe.ingredients
    .map((ingredient, index) => ({ ingredient, index }))
    .filter(({ ingredient }) => ingredient.step === stepIndex + 1)
}
