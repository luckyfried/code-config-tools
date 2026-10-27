import type { Item } from "./types"

const formats = new Map<string, Intl.NumberFormat>()

export function money(value: number, currency: string): string {
  const fraction = value >= 100 ? 0 : 2
  const key = `${currency}:${fraction}`
  let f = formats.get(key)
  if (!f) {
    try {
      f = new Intl.NumberFormat(undefined, { style: "currency", currency, minimumFractionDigits: fraction, maximumFractionDigits: fraction })
    } catch {
      f = new Intl.NumberFormat(undefined, { style: "currency", currency: "USD", minimumFractionDigits: fraction, maximumFractionDigits: fraction })
    }
    formats.set(key, f)
  }
  return f.format(value)
}

/** Cost per wear, or null for an item with no price; a garment never worn costs its whole price on the first wear. */
export function costPerWear(item: Pick<Item, "price" | "wears">): number | null {
  if (item.price == null) return null
  return Math.round((item.price / Math.max(item.wears, 1)) * 100) / 100
}
