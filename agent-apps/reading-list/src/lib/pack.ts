import type { Article } from "@/types"

/** How a story sits on the front page; the card's layout follows from it. */
export type Shape = "lead" | "long" | "tall" | "wide" | "small"

export interface Place {
  c: number
  r: number
  cs: number
  rs: number
  shape: Shape
}

const sentences = (a: Article) => a.summary.join(" ").length

/**
 * The shape a story asks for: the lead spans the width, a story with its brief opens into a long read, and the rest
 * take their size from the picture's shape and the summary's length. `ratio` is the picture's width over height.
 */
export function askShape(a: Article, ratio: number, lead: boolean): Shape {
  if (lead) return "lead"
  if (a.deep) return "long"
  if (ratio < 0.92) return "tall"
  const length = sentences(a)
  if (ratio >= 1.6 && length > 200) return "wide"
  if (ratio >= 1.2 && length > 300) return "wide"
  return "small"
}

const span = (shape: Shape, cols: number): [number, number] => {
  switch (shape) {
    case "lead":
      return [cols, 1]
    case "long":
      return [Math.min(2, cols), 2]
    case "tall":
      return [1, 2]
    case "wide":
      return [Math.min(2, cols), 1]
    default:
      return [1, 1]
  }
}

/**
 * Places every story on a `cols`-wide grid, each in the first free spot it fits reading row by row (dense packing),
 * then grows a neighbor into every hole that is left so the page has no gap.
 */
export function pack(items: { id: string; shape: Shape }[], cols: number): Map<string, Place> {
  const places = new Map<string, Place>()
  const grid: (string | null)[][] = []
  const row = (r: number) => {
    while (grid.length <= r) grid.push(new Array<string | null>(cols).fill(null))
    return grid[r]
  }
  const free = (r: number, c: number, cs: number, rs: number) => {
    if (c + cs > cols) return false
    for (let y = r; y < r + rs; y++) for (let x = c; x < c + cs; x++) if (row(y)[x] !== null) return false
    return true
  }
  const fill = (id: string, r: number, c: number, cs: number, rs: number) => {
    for (let y = r; y < r + rs; y++) for (let x = c; x < c + cs; x++) row(y)[x] = id
  }

  for (const it of items) {
    const [cs, rs] = span(it.shape, cols)
    let r = 0
    for (;;) {
      const c = [...Array(cols).keys()].find((x) => free(r, x, cs, rs))
      if (c !== undefined) {
        fill(it.id, r, c, cs, rs)
        places.set(it.id, { c, r, cs, rs, shape: it.shape })
        break
      }
      r++
    }
  }

  // Grow a neighbor into each hole: the story to its left, then the one above, then the one to its right.
  const last = grid.length - 1
  for (let pass = 0; pass < cols * grid.length; pass++) {
    let grew = false
    for (let r = 0; r <= last && !grew; r++) {
      for (let c = 0; c < cols && !grew; c++) {
        if (row(r)[c] !== null) continue
        const tries: [string | null, (p: Place) => Place | null][] = [
          [c > 0 ? row(r)[c - 1] : null, (p) => (p.c + p.cs === c && free(p.r, c, 1, p.rs) ? { ...p, cs: p.cs + 1 } : null)],
          [r > 0 ? row(r - 1)[c] : null, (p) => (p.r + p.rs === r && free(r, p.c, p.cs, 1) ? { ...p, rs: p.rs + 1 } : null)],
          [c < cols - 1 ? row(r)[c + 1] : null, (p) => (p.c === c + 1 && free(p.r, c, 1, p.rs) ? { ...p, c: c, cs: p.cs + 1 } : null)],
        ]
        for (const [id, grow] of tries) {
          if (!id) continue
          const p = places.get(id)!
          if (p.shape === "lead") continue
          const next = grow(p)
          if (!next) continue
          fill(id, next.r, next.c, next.cs, next.rs)
          places.set(id, next)
          grew = true
          break
        }
      }
    }
    if (!grew) break
  }
  return places
}

/** The card layout a placed story draws with, from the room it was given. */
export function drawnShape(p: Place): Shape {
  if (p.shape === "lead" || p.shape === "long") return p.shape
  if (p.rs >= 2) return "tall"
  if (p.cs >= 2) return "wide"
  return "small"
}
