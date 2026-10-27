/** Hue in degrees and chroma from 0 to 1 for a #rrggbb color. */
export function hueOf(hex: string): { hue: number; chroma: number; light: number } {
  const n = parseInt(hex.slice(1), 16)
  const r = ((n >> 16) & 255) / 255
  const g = ((n >> 8) & 255) / 255
  const b = (n & 255) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const chroma = max - min
  let hue = 0
  if (chroma > 0) {
    if (max === r) hue = ((g - b) / chroma + 6) % 6
    else if (max === g) hue = (b - r) / chroma + 2
    else hue = (r - g) / chroma + 4
    hue *= 60
  }
  return { hue, chroma, light: (max + min) / 2 }
}

/** Below this chroma a color reads as a neutral. */
const NEUTRAL = 0.09
/** Below this chroma, as shown after dust fades it, a chip joins the neutral run at the end of the strip. */
const STRIP_NEUTRAL = 0.12

/**
 * The paint-chip order: chromatic colors by hue, starting at red, then one run of whites, creams, grays, and blacks
 * from light to dark. Dust fades a chip on screen, so a faded chip sorts with the neutrals. Returns a number to sort on.
 */
export function hueKey(hex: string, dust = 0): number {
  const { hue, chroma, light } = hueOf(hex)
  if (chroma * (1 - dust * 0.88) < STRIP_NEUTRAL) return 1000 + (1 - light) * 100
  return (hue + 345) % 360
}

export function isHueSorted(keys: number[]): boolean {
  for (let i = 1; i < keys.length; i++) if (keys[i] < keys[i - 1]) return false
  return true
}

/** "dark" for near-black pieces, "light" for near-white ones; each theme rims the one that melts into its ground. */
export function toneOf(hex: string): "dark" | "light" | "mid" {
  const n = parseInt(hex.slice(1), 16)
  const lum = 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)
  return lum < 72 ? "dark" : lum > 205 ? "light" : "mid"
}

/** True when dark text reads better than light text on this color. */
export function isLight(hex: string): boolean {
  const n = parseInt(hex.slice(1), 16)
  const lum = 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255)
  return lum > 150
}

export const COLOR_FAMILIES = ["red", "orange", "yellow", "green", "blue", "purple", "pink", "neutral"] as const
export type ColorFamily = (typeof COLOR_FAMILIES)[number]

/** The family a color filter groups this color under. */
export function colorFamily(hex: string): ColorFamily {
  const { hue, chroma, light } = hueOf(hex)
  if (chroma < NEUTRAL) return "neutral"
  if (hue >= 18 && hue < 45 && light < 0.42) return "neutral"
  if (hue < 12 || hue >= 345) return light > 0.62 ? "pink" : "red"
  if (hue < 38) return "orange"
  if (hue < 64) return "yellow"
  if (hue < 170) return "green"
  if (hue < 250) return "blue"
  if (hue < 300) return "purple"
  return "pink"
}
