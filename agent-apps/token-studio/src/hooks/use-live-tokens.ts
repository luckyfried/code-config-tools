import { useLayoutEffect, useMemo } from "react"
import { fontStack, SURFACE_ROLES, type System } from "@/lib/tokens"

type Vars = Record<string, string>
type Group = "brand" | "neutral" | "surface" | "type" | "space" | "font"
type Groups = Record<Group, Vars>

function varsOf(sys: System): Groups {
  const g: Groups = { brand: {}, neutral: {}, surface: {}, type: {}, space: {}, font: {} }
  for (const role of SURFACE_ROLES) {
    g.surface[`--l-${role}`] = sys.light[role].hex
    g.surface[`--d-${role}`] = sys.dark[role].hex
  }
  for (const step of sys.brand) g.brand[`--${step.name}`] = step.hex
  for (const step of sys.neutral) g.neutral[`--${step.name}`] = step.hex
  for (const t of sys.type) {
    g.type[`--t-${t.name}`] = `${t.px}px`
    g.type[`--tn-${t.name}`] = String(t.px)
  }
  sys.space.forEach((sp, i) => {
    g.space[`--s-${i + 1}`] = `${sp.px}px`
    g.space[`--sn-${i + 1}`] = String(sp.px)
  })
  g.type["--stair-k"] = String(Math.min(1, 56 / sys.type[sys.type.length - 1].px))
  // The preview tries the person's own fonts first, then the ones that ship with the page.
  g.font["--p-sans"] = fontStack(sys.settings.fonts.sans, '"Inter Variable", ui-sans-serif, system-ui, sans-serif')
  g.font["--p-mono"] = fontStack(sys.settings.fonts.mono, '"JetBrains Mono Variable", ui-monospace, monospace')
  return g
}

/** The variables one live element reads: the groups its `data-live` names, or every group when it names none. */
function pick(groups: Groups, names: string) {
  const v: Vars = {}
  for (const name of names ? (names.split(" ") as Group[]) : (Object.keys(groups) as Group[])) Object.assign(v, groups[name])
  return v
}

const applied = new WeakMap<HTMLElement, Vars>()

function write(el: HTMLElement, vars: Vars) {
  const before = applied.get(el)
  for (const key in vars) if (before?.[key] !== vars[key]) el.style.setProperty(key, vars[key])
  applied.set(el, vars)
}

/** The system last written, for a part of the page that comes back after missing some changes. */
let latest: Groups | null = null

/** A live part inside a region marked `data-away` (scrolled well out of view) waits for that region to come back. */
const ON_SCREEN = "[data-live]:not([data-away] [data-live])"

function writeWithin(root: ParentNode, selector: string) {
  const groups = latest
  if (!groups) return
  root.querySelectorAll<HTMLElement>(selector).forEach((el) => write(el, pick(groups, el.dataset.live ?? "")))
}

/** Brings every live part inside `region` up to the current system. */
export const catchUp = (region: Element) => writeWithin(region, "[data-live]")

/**
 * Writes the generated system as custom properties onto the parts of the page that show it (each marked
 * `data-live`, with the groups it reads, such as `data-live="brand"`), in the same frame as the change. Each part
 * gets only its own groups, so only the parts that show the moving value restyle, and parts scrolled away catch up
 * when they come back.
 */
export function useLiveTokens(sys: System) {
  const groups = useMemo(() => varsOf(sys), [sys])

  useLayoutEffect(() => {
    latest = groups
    writeWithin(document, ON_SCREEN)
  })
}
