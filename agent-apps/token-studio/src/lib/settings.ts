// Where the settings come from: config.js seeds them, this browser keeps them, and a JSON export brings them back.
import { hexToRgb, rgbToOklch } from "./oklch.ts"
import { DEFAULT_SYSTEM, LIMITS, type Settings } from "./tokens.ts"

declare global {
  interface Window {
    __APP_CONFIG__?: unknown
  }
}

const STORAGE_KEY = "token-studio:v1"

const clamp = (n: number, [lo, hi]: readonly [number, number]) => Math.min(hi, Math.max(lo, n))
const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v)
const num = (v: unknown, fallback: number) => (typeof v === "number" && Number.isFinite(v) ? v : fallback)
const text = (v: unknown, fallback: string) => (typeof v === "string" ? v.slice(0, 80) : fallback)

/** Settings from any object shaped like the inputs, a saved system, or an export; null when it is none of them. */
export function toSettings(value: unknown): Settings | null {
  if (!isObject(value)) return null
  const source = isObject(value.settings) ? value.settings : value
  if (!isObject(source.brand)) return null
  const brand = source.brand
  let hue = num(brand.hue, NaN)
  let chroma = num(brand.chroma, NaN)
  const rgb = typeof brand.hex === "string" ? hexToRgb(brand.hex) : null
  if (rgb && (Number.isNaN(hue) || Number.isNaN(chroma))) {
    const [, c, h] = rgbToOklch(rgb)
    hue = Number.isNaN(hue) ? h : hue
    chroma = Number.isNaN(chroma) ? c : chroma
  }
  if (Number.isNaN(hue) || Number.isNaN(chroma)) return null
  const fonts = isObject(source.fonts) ? source.fonts : {}
  const d = DEFAULT_SYSTEM
  return {
    brand: { hue: ((hue % 360) + 360) % 360, chroma: clamp(chroma, LIMITS.chroma) },
    neutralHue: ((num(source.neutralHue, hue) % 360) + 360) % 360,
    typeScaleRatio: clamp(num(source.typeScaleRatio, d.typeScaleRatio), LIMITS.typeScaleRatio),
    baseSize: Math.round(clamp(num(source.baseSize, d.baseSize), LIMITS.baseSize)),
    spacingBase: Math.round(clamp(num(source.spacingBase, d.spacingBase), LIMITS.spacingBase)),
    fonts: { sans: text(fonts.sans, d.fonts.sans), mono: text(fonts.mono, d.fonts.mono) },
  }
}

export type Seed = { settings: Settings; fromConfig: boolean; hex: string | null }

export function readSeed(): Seed {
  const config = window.__APP_CONFIG__
  const settings = toSettings(config)
  const hex = isObject(config) && isObject(config.brand) && typeof config.brand.hex === "string" ? config.brand.hex : null
  return settings ? { settings, fromConfig: true, hex } : { settings: DEFAULT_SYSTEM, fromConfig: false, hex: null }
}

type Saved = { seed: string; settings: Settings }

/** The saved system, when it grew from the same seed; a new seed from config.js starts fresh. */
export function loadSaved(seed: Settings): Settings | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const saved = JSON.parse(raw) as Saved
    if (saved.seed !== JSON.stringify(seed)) return null
    return toSettings(saved.settings)
  } catch {
    return null
  }
}

export function save(seed: Settings, settings: Settings) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ seed: JSON.stringify(seed), settings } satisfies Saved))
  } catch {
    // Private windows can refuse storage; the editor keeps working without it.
  }
}
