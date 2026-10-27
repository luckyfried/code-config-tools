// What the person sets on this machine, under the one key "recipe-box": the box's filter and the ticked list lines.
// A filter is a status, or "tag:<tag>" for the recipes carrying that tag.
export type Filter = "box" | "new" | "kept" | "week" | "skipped" | `tag:${string}`

export interface Local {
  filter: Filter
  ticked: Record<string, string[]>
}

const KEY = "recipe-box"
const EMPTY: Local = { filter: "box", ticked: {} }

export function readLocal(): Local {
  try {
    const raw = window.localStorage.getItem(KEY)
    if (!raw) return EMPTY
    const value = JSON.parse(raw) as Partial<Local>
    return { ...EMPTY, ...value, ticked: value.ticked ?? {} }
  } catch {
    return EMPTY
  }
}

export function writeLocal(value: Local) {
  try {
    window.localStorage.setItem(KEY, JSON.stringify(value))
  } catch {
    // A full or blocked storage keeps the choice for this visit only.
  }
}
