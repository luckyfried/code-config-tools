// The token system: the few numbers a person tunes, and everything generated from them.
import { clampChroma, contrast, oklchToRgb, rgbToHex, type Rgb } from "./oklch.ts"

export type Settings = {
  brand: { hue: number; chroma: number }
  neutralHue: number
  typeScaleRatio: number
  baseSize: number
  spacingBase: number
  fonts: { sans: string; mono: string }
}

export const DEFAULT_SYSTEM: Settings = {
  brand: { hue: 262, chroma: 0.17 },
  neutralHue: 255,
  typeScaleRatio: 1.25,
  baseSize: 16,
  spacingBase: 4,
  fonts: { sans: "Inter", mono: "JetBrains Mono" },
}

export const LIMITS = {
  hue: [0, 360],
  chroma: [0.02, 0.37],
  typeScaleRatio: [1.067, 1.618],
  baseSize: [12, 22],
  spacingBase: [2, 8],
} as const

export type Color = { l: number; c: number; h: number; rgb: Rgb; hex: string; css: string; clamped: boolean }
export type Step = Color & { name: string; step: number }

export const STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900] as const
const LIGHTNESS = [0.971, 0.936, 0.885, 0.815, 0.733, 0.648, 0.564, 0.484, 0.405, 0.33]
const BRAND_CHROMA = [0.14, 0.3, 0.52, 0.76, 0.92, 1, 0.97, 0.86, 0.72, 0.58]
const NEUTRAL_CHROMA = [0.003, 0.005, 0.007, 0.009, 0.011, 0.013, 0.014, 0.014, 0.014, 0.013]

const round = (n: number, places: number) => Number(n.toFixed(places))

export function color(l: number, c: number, h: number): Color {
  const fit = clampChroma(l, c, h)
  const rgb = oklchToRgb(l, fit.c, h)
  const hue = round(((h % 360) + 360) % 360, 1)
  return {
    l,
    c: fit.c,
    h: hue,
    rgb,
    hex: rgbToHex(rgb),
    css: `oklch(${round(l * 100, 1)}% ${round(fit.c, 3)} ${hue})`,
    clamped: fit.clamped,
  }
}

function ramp(prefix: string, chromas: number[], h: number): Step[] {
  return STEPS.map((step, i) => ({ ...color(LIGHTNESS[i], chromas[i], h), name: `${prefix}-${step}`, step }))
}

export const SURFACE_ROLES = ["bg", "surface", "surface-2", "border", "text", "muted", "accent", "on-accent", "accent-soft", "on-accent-soft"] as const
export type SurfaceRole = (typeof SURFACE_ROLES)[number]
export type Surfaces = Record<SurfaceRole, Color>

/** The text that reads best on `bg`: white, or the brand's own deep shade. */
function bestOn(bg: Color, light: Color, dark: Color) {
  return contrast(light.rgb, bg.rgb) >= contrast(dark.rgb, bg.rgb) ? light : dark
}

function surfaces(brand: Step[], s: Settings, mode: "light" | "dark"): Surfaces {
  const nh = s.neutralHue
  const bh = s.brand.hue
  const white = color(0.995, 0.002, nh)
  const ink = color(0.2, Math.min(0.05, s.brand.chroma * 0.4), bh)
  if (mode === "light") {
    const accent = brand[6]
    return {
      bg: color(0.982, 0.004, nh),
      surface: white,
      "surface-2": color(0.955, 0.007, nh),
      border: color(0.9, 0.009, nh),
      text: color(0.235, 0.016, nh),
      muted: color(0.52, 0.016, nh),
      accent,
      "on-accent": bestOn(accent, white, ink),
      "accent-soft": brand[1],
      "on-accent-soft": brand[7],
    }
  }
  const accent = brand[4]
  return {
    bg: color(0.18, 0.012, nh),
    surface: color(0.225, 0.014, nh),
    "surface-2": color(0.265, 0.015, nh),
    border: color(0.33, 0.016, nh),
    text: color(0.955, 0.006, nh),
    muted: color(0.73, 0.014, nh),
    accent,
    "on-accent": bestOn(accent, white, ink),
    "accent-soft": color(0.3, s.brand.chroma * 0.42, bh),
    "on-accent-soft": brand[2],
  }
}

export const TYPE_STEPS = [
  { name: "xs", n: -2 },
  { name: "sm", n: -1 },
  { name: "base", n: 0 },
  { name: "lg", n: 1 },
  { name: "xl", n: 2 },
  { name: "2xl", n: 3 },
  { name: "3xl", n: 4 },
  { name: "4xl", n: 5 },
] as const

export const SPACE_STEPS = [1, 2, 3, 4, 6, 8, 12, 16] as const

export const MATRIX_FG = [
  { role: "text", label: "Text" },
  { role: "muted", label: "Muted" },
  { role: "accent", label: "Brand" },
  { role: "on-accent", label: "On brand" },
] as const
export const MATRIX_BG = [
  { role: "bg", label: "Page" },
  { role: "surface", label: "Card" },
  { role: "accent-soft", label: "Soft" },
  { role: "accent", label: "Brand" },
] as const

export type Pair = { fg: SurfaceRole; bg: SurfaceRole; ratio: number; level: "AAA" | "AA" | "" }

/** Keeps the last value per slice, so a slice whose inputs did not move keeps its identity and its view skips a render. */
function remember<T>(make: (key: string) => T) {
  let last: { key: string; value: T } | null = null
  return (key: string) => {
    if (last?.key !== key) last = { key, value: make(key) }
    return last.value
  }
}

let current: Settings = DEFAULT_SYSTEM
const brandRamp = remember(() => ramp("brand", BRAND_CHROMA.map((k) => k * current.brand.chroma), current.brand.hue))
const neutralRamp = remember(() => ramp("neutral", NEUTRAL_CHROMA, current.neutralHue))
const surfacePair = remember(() => {
  const brand = brandRamp(`${current.brand.hue} ${current.brand.chroma}`)
  const light = surfaces(brand, current, "light")
  const dark = surfaces(brand, current, "dark")
  return { light, dark, pairs: { light: pairsOf(light), dark: pairsOf(dark) } }
})
const typeScale = remember(() =>
  TYPE_STEPS.map(({ name, n }) => {
    const px = current.baseSize * current.typeScaleRatio ** n
    return { name, px: round(px, 2), rem: round(px / 16, 3) }
  }),
)
const spaceScale = remember(() => SPACE_STEPS.map((k, i) => ({ name: `space-${i + 1}`, px: k * current.spacingBase })))

function pairsOf(sf: Surfaces): Pair[] {
  return MATRIX_FG.flatMap(({ role: fg }) =>
    MATRIX_BG.map(({ role: bg }) => {
      const ratio = contrast(sf[fg].rgb, sf[bg].rgb)
      return { fg, bg, ratio, level: ratio >= 7 ? "AAA" : ratio >= 4.5 ? "AA" : "" } as Pair
    }),
  )
}

export function buildSystem(s: Settings) {
  current = s
  const brandKey = `${s.brand.hue} ${s.brand.chroma}`
  const { light, dark, pairs } = surfacePair(`${brandKey} ${s.neutralHue}`)
  return {
    settings: s,
    brand: brandRamp(brandKey),
    neutral: neutralRamp(String(s.neutralHue)),
    light,
    dark,
    type: typeScale(`${s.baseSize} ${s.typeScaleRatio}`),
    space: spaceScale(String(s.spacingBase)),
    pairs,
  }
}

export type System = ReturnType<typeof buildSystem>

export const fontStack = (name: string, fallback: string) => {
  const trimmed = name.trim()
  return trimmed ? `"${trimmed.replace(/"/g, "")}", ${fallback}` : fallback
}
export const sansStack = (s: Settings) => fontStack(s.fonts.sans, "ui-sans-serif, system-ui, sans-serif")
export const monoStack = (s: Settings) => fontStack(s.fonts.mono, "ui-monospace, SFMono-Regular, monospace")

/** The tokens.css the person downloads. */
export function toCss(sys: System): string {
  const s = sys.settings
  const surfaceLines = (sf: Surfaces, indent: string) =>
    SURFACE_ROLES.map((role) => `${indent}--color-${role}: ${sf[role].css};`).join("\n")
  const lines = [
    `/* tokens.css, made in Token Studio. Brand hue ${round(s.brand.hue, 1)}, chroma ${round(s.brand.chroma, 3)}; neutral hue ${round(s.neutralHue, 1)}. */`,
    ":root {",
    "  /* Brand ramp */",
    ...sys.brand.map((c) => `  --color-${c.name}: ${c.css}; /* ${c.hex} */`),
    "",
    "  /* Neutral ramp */",
    ...sys.neutral.map((c) => `  --color-${c.name}: ${c.css}; /* ${c.hex} */`),
    "",
    "  /* Surfaces, light */",
    surfaceLines(sys.light, "  "),
    "",
    "  /* Type */",
    `  --font-sans: ${sansStack(s)};`,
    `  --font-mono: ${monoStack(s)};`,
    ...sys.type.map((t) => `  --text-${t.name}: ${t.rem}rem; /* ${t.px}px */`),
    "  --leading-tight: 1.15;",
    "  --leading-body: 1.55;",
    "",
    "  /* Space */",
    ...sys.space.map((sp) => `  --${sp.name}: ${sp.px / 16}rem; /* ${sp.px}px */`),
    "}",
    "",
    "@media (prefers-color-scheme: dark) {",
    '  :root:not([data-theme="light"]) {',
    surfaceLines(sys.dark, "    "),
    "  }",
    "}",
    "",
    '[data-theme="dark"] {',
    surfaceLines(sys.dark, "  "),
    "}",
    "",
  ]
  return lines.join("\n")
}

/** The JSON export: the settings that resume the system, and every generated value. */
export function toJson(sys: System): string {
  const colors = (list: Step[]) => Object.fromEntries(list.map((c) => [c.step, { oklch: c.css, hex: c.hex }]))
  const roles = (sf: Surfaces) => Object.fromEntries(SURFACE_ROLES.map((r) => [r, { oklch: sf[r].css, hex: sf[r].hex }]))
  return `${JSON.stringify(
    {
      app: "token-studio",
      version: 1,
      settings: sys.settings,
      tokens: {
        brand: colors(sys.brand),
        neutral: colors(sys.neutral),
        light: roles(sys.light),
        dark: roles(sys.dark),
        type: Object.fromEntries(sys.type.map((t) => [t.name, `${t.rem}rem`])),
        space: Object.fromEntries(sys.space.map((sp) => [sp.name, `${sp.px}px`])),
      },
    },
    null,
    2,
  )}\n`
}
