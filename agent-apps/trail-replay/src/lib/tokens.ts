/** Theme colors read from the CSS variables in theme.css, resolved to rgba() so MapLibre and canvas take them as is. */

export type RGBA = [number, number, number, number]

let probe: CanvasRenderingContext2D | null = null

export function resolveColor(value: string): RGBA {
  if (!probe) {
    const canvas = document.createElement("canvas")
    canvas.width = canvas.height = 1
    probe = canvas.getContext("2d", { willReadFrequently: true })
  }
  if (!probe) return [0, 0, 0, 1]
  probe.clearRect(0, 0, 1, 1)
  probe.fillStyle = "#000"
  probe.fillStyle = value.trim() || "#000"
  probe.fillRect(0, 0, 1, 1)
  const [r, g, b, a] = probe.getImageData(0, 0, 1, 1).data
  return [r, g, b, a / 255]
}

export const rgba = ([r, g, b, a]: RGBA, alpha = a) => `rgba(${r}, ${g}, ${b}, ${Math.round(alpha * 1000) / 1000})`

export function cssVar(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim()
}

export function token(name: string, alpha?: number) {
  return rgba(resolveColor(cssVar(name)), alpha)
}

export function tokenNumber(name: string, fallback: number) {
  const value = Number.parseFloat(cssVar(name))
  return Number.isFinite(value) ? value : fallback
}

export function ramp(): RGBA[] {
  return [1, 2, 3, 4, 5].map((n) => resolveColor(cssVar(`ramp-${n}`)))
}

/** A color along the ramp, `t` from 0 (low) to 1 (high). */
export function rampAt(colors: RGBA[], t: number, alpha?: number) {
  const x = Math.min(1, Math.max(0, t)) * (colors.length - 1)
  const i = Math.min(colors.length - 2, Math.floor(x))
  const f = x - i
  const a = colors[i]
  const b = colors[i + 1]
  const c: RGBA = [
    Math.round(a[0] + (b[0] - a[0]) * f),
    Math.round(a[1] + (b[1] - a[1]) * f),
    Math.round(a[2] + (b[2] - a[2]) * f),
    1,
  ]
  return rgba(c, alpha ?? 1)
}

const dark = window.matchMedia("(prefers-color-scheme: dark)")

export const isDark = () => dark.matches

/** Calls `fn` when the device switches between light and dark. */
export function onSchemeChange(fn: () => void) {
  dark.addEventListener("change", fn)
  return () => dark.removeEventListener("change", fn)
}
