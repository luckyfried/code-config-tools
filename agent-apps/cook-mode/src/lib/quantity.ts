import type { Ingredient, Units } from "./config"

type Kind = "mass" | "volume" | "count"

interface UnitInfo {
  kind: Kind
  /** Grams for mass, milliliters for volume. */
  base: number
  label: string
  system: "metric" | "us" | "both"
}

const UNITS: Record<string, UnitInfo> = {
  g: { kind: "mass", base: 1, label: "g", system: "metric" },
  kg: { kind: "mass", base: 1000, label: "kg", system: "metric" },
  oz: { kind: "mass", base: 28.3495, label: "oz", system: "us" },
  lb: { kind: "mass", base: 453.592, label: "lb", system: "us" },
  ml: { kind: "volume", base: 1, label: "ml", system: "metric" },
  l: { kind: "volume", base: 1000, label: "l", system: "metric" },
  tsp: { kind: "volume", base: 4.92892, label: "tsp", system: "both" },
  tbsp: { kind: "volume", base: 14.7868, label: "tbsp", system: "both" },
  cup: { kind: "volume", base: 236.588, label: "cup", system: "us" },
  "fl oz": { kind: "volume", base: 29.5735, label: "fl oz", system: "us" },
}

const ALIASES: Record<string, string> = {
  gram: "g", grams: "g", kilo: "kg", kilogram: "kg", kilograms: "kg",
  ounce: "oz", ounces: "oz", pound: "lb", pounds: "lb", lbs: "lb",
  milliliter: "ml", milliliters: "ml", millilitre: "ml", millilitres: "ml", mL: "ml",
  liter: "l", liters: "l", litre: "l", litres: "l", L: "l",
  teaspoon: "tsp", teaspoons: "tsp", tablespoon: "tbsp", tablespoons: "tbsp", tbs: "tbsp",
  cups: "cup", "fluid ounce": "fl oz", "fluid ounces": "fl oz",
}

function unitKey(unit: string) {
  const trimmed = unit.trim()
  if (UNITS[trimmed]) return trimmed
  const lower = trimmed.toLowerCase()
  if (UNITS[lower]) return lower
  return ALIASES[trimmed] ?? ALIASES[lower] ?? null
}

const GLYPH: Record<number, string> = {
  0.125: "⅛", 0.25: "¼", 0.375: "⅜", 0.5: "½", 0.625: "⅝", 0.75: "¾", 0.875: "⅞",
}
const THIRDS: Record<number, string> = { [1 / 3]: "⅓", [2 / 3]: "⅔" }

/** The fractions each kind of measure is really read in. */
export const STEPS = {
  eighths: [0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1],
  kitchen: [0, 0.25, 1 / 3, 0.5, 2 / 3, 0.75, 1],
  spoons: [0, 0.125, 0.25, 0.5, 0.75, 1],
  halves: [0, 0.5, 1],
}

/** 1.5 → "1½", 0.333 → "⅓": the nearest step the measure allows, in real fraction glyphs. */
export function fractionText(value: number, steps: number[] = STEPS.kitchen) {
  if (value >= 10) return String(Math.round(value))
  let whole = Math.floor(value)
  const rest = value - whole
  let best = steps[0]
  for (const option of steps) if (Math.abs(option - rest) < Math.abs(best - rest)) best = option
  if (best === 1) {
    whole += 1
    best = 0
  }
  if (whole === 0 && best === 0) best = steps[1]
  const glyph = best === 0 ? "" : (GLYPH[best] ?? THIRDS[best] ?? "")
  return `${whole === 0 ? "" : whole}${glyph}`
}

function metricText(value: number) {
  if (value >= 100) return String(Math.round(value / 5) * 5)
  if (value >= 10) return String(Math.round(value))
  return String(Math.round(value * 2) / 2)
}

function cleanDecimal(value: number) {
  return String(Math.round(value * 100) / 100)
}

export interface Shown {
  amount: string
  unit: string
  /** A comparable key for adding up the same thing across recipes. */
  key: string
  value: number | null
}

/** One quantity, scaled and shown in the person's units. */
export function showQuantity(amount: number | null, unit: string, factor: number, units: Units): Shown {
  if (amount === null || amount === undefined) return { amount: "", unit: unit.trim(), key: unit.trim(), value: null }
  const scaled = amount * factor
  const key = unitKey(unit)
  if (!key) {
    return { amount: fractionText(scaled), unit: unit.trim(), key: unit.trim().toLowerCase(), value: scaled }
  }
  const info = UNITS[key]
  const base = scaled * info.base
  if (info.kind === "mass") {
    if (units === "metric") {
      return base >= 1000
        ? { amount: cleanDecimal(base / 1000), unit: "kg", key: "g", value: base }
        : { amount: metricText(base), unit: "g", key: "g", value: base }
    }
    const ounces = base / UNITS.oz.base
    return ounces >= 16
      ? { amount: fractionText(ounces / 16, ounces >= 32 ? STEPS.spoons : STEPS.eighths), unit: "lb", key: "g", value: base }
      : { amount: fractionText(ounces, ounces >= 4 ? STEPS.halves : STEPS.spoons), unit: "oz", key: "g", value: base }
  }
  // Spoons stay spoons while they are spoon-sized: under a quarter cup, or eight tablespoons in metric.
  if (info.system === "both" && base < (units === "metric" ? UNITS.tbsp.base * 8.5 : UNITS.cup.base / 4)) {
    const spoon = base >= UNITS.tbsp.base ? "tbsp" : "tsp"
    return { amount: fractionText(base / UNITS[spoon].base, STEPS.spoons), unit: spoon, key: "ml", value: base }
  }
  if (units === "metric") {
    return base >= 1000
      ? { amount: cleanDecimal(base / 1000), unit: "l", key: "ml", value: base }
      : { amount: metricText(base), unit: "ml", key: "ml", value: base }
  }
  if (base < UNITS.tbsp.base) return { amount: fractionText(base / UNITS.tsp.base, STEPS.spoons), unit: "tsp", key: "ml", value: base }
  if (base < UNITS.cup.base / 4) return { amount: fractionText(base / UNITS.tbsp.base, STEPS.spoons), unit: "tbsp", key: "ml", value: base }
  const cups = fractionText(base / UNITS.cup.base)
  return { amount: cups, unit: cups === "1" || /^[⅛¼⅓⅜½⅝⅔¾⅞]$/.test(cups) ? "cup" : "cups", key: "ml", value: base }
}

/** The ingredient's name, made singular when there is one or less of a counted thing. */
export function nameFor(ingredient: Ingredient, shown: Shown) {
  const name = ingredient.name
  if (shown.unit !== "" || shown.value === null || shown.value > 1) return name
  const [head, ...rest] = name.split(",")
  const words = head.split(" ")
  const last = words[words.length - 1]
  let single = last
  if (/[^aeiou]ies$/.test(last)) single = last.slice(0, -3) + "y"
  else if (/oes$/.test(last)) single = last.slice(0, -2)
  else if (/[^s]s$/.test(last)) single = last.slice(0, -1)
  words[words.length - 1] = single
  return [words.join(" "), ...rest].join(",")
}

export function shownIngredient(ingredient: Ingredient, factor: number, units: Units) {
  const shown = showQuantity(ingredient.amount, ingredient.unit, factor, units)
  return { ...shown, name: nameFor(ingredient, shown) }
}

/** Oven temperatures in step text follow the person's units. */
export function convertTemperatures(text: string, units: Units) {
  return text.replace(/(\d{2,3})\s?°\s?([CF])\b/g, (match, degrees: string, scale: string) => {
    const value = Number(degrees)
    // Oven dials step by 25 °F and 10 °C.
    if (units === "us" && scale === "C") return `${Math.round(((value * 9) / 5 + 32) / 25) * 25}°F`
    if (units === "metric" && scale === "F") return `${Math.round(((value - 32) * 5) / 9 / 10) * 10}°C`
    return match
  })
}
