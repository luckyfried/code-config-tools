import type { Item } from "./config"

export function moneyFormat(currency: string, items: Item[]): Intl.NumberFormat {
  const whole = items.every((item) => Number.isInteger(item.price))
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency,
      minimumFractionDigits: whole ? 0 : 2,
      maximumFractionDigits: whole ? 0 : 2,
    })
  } catch {
    return new Intl.NumberFormat(undefined, { minimumFractionDigits: whole ? 0 : 2, maximumFractionDigits: 2 })
  }
}

export interface Band {
  id: string
  low: number
  high: number
}

const STEPS = [1, 1.5, 2, 2.5, 3, 4, 5, 7.5]

/** The smallest round amount at or above a price: 48 becomes 50, 129 becomes 150. */
function roundUp(value: number): number {
  if (value <= 1) return 1
  const power = Math.pow(10, Math.floor(Math.log10(value)))
  for (const step of STEPS) if (step * power >= value) return step * power
  return 10 * power
}

/** Three price bands cut near the thirds of the list at round amounts. */
export function priceBands(items: Item[]): Band[] {
  const prices = items.map((item) => item.price).sort((a, b) => a - b)
  if (prices.length < 3) return []
  const at = (q: number) => prices[Math.min(prices.length - 1, Math.floor(q * prices.length))]
  const low = roundUp(at(1 / 3))
  let high = roundUp(at(2 / 3))
  if (high <= low) high = roundUp(low * 1.5)
  const bands = [
    { id: "low", low: 0, high: low },
    { id: "mid", low, high },
    { id: "high", low: high, high: Infinity },
  ]
  return bands.filter((band) => prices.some((p) => p >= band.low && p < band.high))
}

export function inBand(item: Item, band: Band | undefined): boolean {
  return !band || (item.price >= band.low && item.price < band.high)
}
