// OKLCH and sRGB conversion, gamut clamping, and WCAG contrast, after Björn Ottosson's Oklab definition.

export type Rgb = [number, number, number]

const cube = (x: number) => x * x * x
const toLinear = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
const toGamma = (c: number) => (c <= 0.0031308 ? 12.92 * c : 1.055 * Math.sign(c) * Math.abs(c) ** (1 / 2.4) - 0.055)

/** Oklab from the cone responses (l, m, s), each already cube-rooted. */
function lmsToOklab(l: number, m: number, s: number): Rgb {
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ]
}

/** Oklab from CIE XYZ (D65), the form of Ottosson's published test table. */
export function xyzToOklab([x, y, z]: Rgb): Rgb {
  return lmsToOklab(
    Math.cbrt(0.8189330101 * x + 0.3618667424 * y - 0.1288597137 * z),
    Math.cbrt(0.0329845436 * x + 0.9293118715 * y + 0.0361456387 * z),
    Math.cbrt(0.0482003018 * x + 0.2643662691 * y + 0.633851707 * z),
  )
}

/** Oklab from gamma-encoded sRGB in 0..1. */
export function rgbToOklab(rgb: Rgb): Rgb {
  const [r, g, b] = rgb.map(toLinear)
  return lmsToOklab(
    Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b),
    Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b),
    Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b),
  )
}

/** Gamma-encoded sRGB from OKLCH, unclamped: a channel outside 0..1 is out of gamut. */
export function oklchToRgb(l: number, c: number, h: number): Rgb {
  const a = c * Math.cos((h * Math.PI) / 180)
  const b = c * Math.sin((h * Math.PI) / 180)
  const lc = cube(l + 0.3963377774 * a + 0.2158037573 * b)
  const mc = cube(l - 0.1055613458 * a - 0.0638541728 * b)
  const sc = cube(l - 0.0894841775 * a - 1.291485548 * b)
  return [
    4.0767416621 * lc - 3.3077115913 * mc + 0.2309699292 * sc,
    -1.2684380046 * lc + 2.6097574011 * mc - 0.3413193965 * sc,
    -0.0041960863 * lc - 0.7034186147 * mc + 1.707614701 * sc,
  ].map(toGamma) as Rgb
}

export function rgbToOklch(rgb: Rgb): Rgb {
  const [l, a, b] = rgbToOklab(rgb)
  const h = (Math.atan2(b, a) * 180) / Math.PI
  return [l, Math.hypot(a, b), h < 0 ? h + 360 : h]
}

const EPSILON = 1e-4
export const inGamut = (rgb: Rgb) => rgb.every((c) => c >= -EPSILON && c <= 1 + EPSILON)

/** The most chroma up to `c` that stays inside sRGB at this lightness and hue; `clamped` when it had to give some up. */
export function clampChroma(l: number, c: number, h: number): { c: number; clamped: boolean } {
  if (inGamut(oklchToRgb(l, c, h))) return { c, clamped: false }
  let lo = 0
  let hi = c
  for (let i = 0; i < 18; i++) {
    const mid = (lo + hi) / 2
    if (inGamut(oklchToRgb(l, mid, h))) lo = mid
    else hi = mid
  }
  return { c: lo, clamped: c - lo > 0.002 }
}

const clamp01 = (c: number) => Math.min(1, Math.max(0, c))

export function rgbToHex(rgb: Rgb): string {
  return `#${rgb.map((c) => Math.round(clamp01(c) * 255).toString(16).padStart(2, "0")).join("")}`
}

export function hexToRgb(hex: string): Rgb | null {
  const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return null
  const digits = m[1].length === 3 ? [...m[1]].map((d) => d + d).join("") : m[1]
  return [0, 2, 4].map((i) => parseInt(digits.slice(i, i + 2), 16) / 255) as Rgb
}

/** WCAG 2 relative luminance and contrast ratio. */
export function luminance(rgb: Rgb): number {
  const [r, g, b] = rgb.map((c) => toLinear(clamp01(c)))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function contrast(a: Rgb, b: Rgb): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}
