import type { Bracket, Entrant, Match } from "@/lib/bracket"

// The sheet is two-sided: the top half of the field runs left to right, the bottom half right to left, and the
// final sits in a wider center column with the champion's slot and banner above it. Units are SVG user units.

export const CHIP_W = 196
export const CHIP_H = 32
export const GAP_IN = 4
export const MATCH_H = CHIP_H * 2 + GAP_IN
export const COL_GAP = 22
export const CENTER_W = 244
export const TOP = 40
export const CHAMP_H = 40
export const CHAMP_W = 208

export type Point = { x: number; y: number }

export type ByeGhost = { entrant: Entrant; x: number; y: number; to: { id: string; slot: 0 | 1 } }

export type Layout = {
  width: number
  height: number
  rowH: number
  matchPos: Map<string, Point>
  chip: (id: string, slot: 0 | 1) => Point
  champion: Point
  banner: { x: number; y: number; w: number; h: number }
  columns: { round: number; x: number; side: Match["side"] }[]
  byeGhosts: ByeGhost[]
  connectors: { id: string; from: string; d: string; to: string; slot: 0 | 1 }[]
  finalLink: string
}

/** `minH` stretches the sheet to a taller shape so it fills the space it is shown in. */
export function layout(b: Bracket, minH = 540): Layout {
  const R = b.rounds
  const perSide = Math.max(1, b.size / 4)
  // Rows spread from the first match to the last, so the sheet has no empty half-row above or below.
  const rowH = perSide > 1 ? Math.max(MATCH_H + 24, (minH - TOP - MATCH_H - 8) / (perSide - 1)) : 0
  const used = TOP + MATCH_H + 8 + (perSide - 1) * rowH
  const height = Math.max(minH, used)
  const first = TOP + MATCH_H / 2 + (height - used) / 2
  const step = CHIP_W + COL_GAP
  const centerLeft = (R - 1) * step
  const width = 2 * (R - 1) * step + CENTER_W

  const colX = (round: number, side: Match["side"]) => {
    if (side === "center") return centerLeft + (CENTER_W - CHIP_W) / 2
    if (side === "left") return (round - 1) * step
    return centerLeft + CENTER_W + COL_GAP + (R - 1 - round) * step
  }
  // Center of position j (counted within its side) in a round: halfway between the two positions that feed it.
  const rowY = (round: number, j: number) => {
    const span = 2 ** (round - 1)
    return first + (j * span + (span - 1) / 2) * rowH
  }
  const sideIndex = (round: number, pos: number, side: Match["side"]) => {
    const count = b.size / 2 ** round
    return side === "right" ? pos - count / 2 : pos
  }

  const matchPos = new Map<string, Point>()
  for (const m of b.matches) {
    const y = m.side === "center" ? first + ((perSide - 1) * rowH) / 2 : rowY(m.round, sideIndex(m.round, m.pos, m.side))
    matchPos.set(m.id, { x: colX(m.round, m.side), y })
  }
  const chip = (id: string, slot: 0 | 1): Point => {
    const p = matchPos.get(id)!
    return { x: p.x, y: slot === 0 ? p.y - CHIP_H - GAP_IN / 2 : p.y + GAP_IN / 2 }
  }

  const finalM = b.byRound[R - 1][0]
  const finalTop = chip(finalM.id, 0).y
  const champion = { x: centerLeft + (CENTER_W - CHAMP_W) / 2, y: finalTop - 56 - CHAMP_H }
  const bannerY = Math.max(TOP - 30, champion.y - 150)
  const banner = { x: centerLeft - 30, y: bannerY, w: CENTER_W + 60, h: Math.min(140, champion.y - bannerY - 10) }

  const link = (from: Point, fromW: number, fromH: number, to: Point, toW: number, toH: number) => {
    const goesRight = from.x < to.x
    const sx = goesRight ? from.x + fromW : from.x
    const sy = from.y + fromH / 2
    const ex = goesRight ? to.x : to.x + toW
    const ey = to.y + toH / 2
    const mx = (sx + ex) / 2
    return `M${sx} ${sy}H${mx}V${ey}H${ex}`
  }

  const connectors: Layout["connectors"] = []
  for (const m of b.matches) {
    if (!m.next) continue
    const p = matchPos.get(m.id)!
    const from = { x: p.x, y: p.y - MATCH_H / 2 }
    const to = chip(m.next.id, m.next.slot)
    connectors.push({ id: `${m.id}>${m.next.id}`, from: m.id, to: m.next.id, slot: m.next.slot, d: link(from, CHIP_W, MATCH_H, to, CHIP_W, CHIP_H) })
  }

  // A bye shows as a faint chip in the first round with a dotted line to the slot it starts in.
  const byeGhosts: ByeGhost[] = []
  if (R >= 2) {
    for (const m of b.byRound[1]) {
      m.slots.forEach((s, slot) => {
        if (s.kind !== "entrant") return
        const k = 2 * m.pos + slot
        const side: Match["side"] = k < b.size / 4 ? "left" : "right"
        const x = colX(1, side)
        const y = rowY(1, sideIndex(1, k, side)) - CHIP_H / 2
        byeGhosts.push({ entrant: s.entrant, x, y, to: { id: m.id, slot: slot as 0 | 1 } })
      })
    }
  }
  for (const g of byeGhosts) {
    const to = chip(g.to.id, g.to.slot)
    connectors.push({ id: `bye:${g.entrant.seed}`, from: "", to: g.to.id, slot: g.to.slot, d: link({ x: g.x, y: g.y }, CHIP_W, CHIP_H, to, CHIP_W, CHIP_H) })
  }

  const fp = matchPos.get(finalM.id)!
  const finalLink = `M${fp.x + CHIP_W / 2} ${finalTop}V${champion.y + CHAMP_H}`

  const columns: Layout["columns"] = []
  for (let r = 1; r < R; r++) {
    columns.push({ round: r, x: colX(r, "left"), side: "left" })
    columns.push({ round: r, x: colX(r, "right"), side: "right" })
  }
  columns.push({ round: R, x: colX(R, "center"), side: "center" })

  return { width, height, rowH, matchPos, chip, champion, banner, columns, byeGhosts, connectors, finalLink }
}

/** The relative luminance of a hex color, 0 for black to 1 for white. */
export function luminance(hex: string): number {
  const h = hex.replace("#", "")
  const full = h.length === 3 ? h.split("").map((c) => c + c).join("") : h
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(full.slice(i, i + 2), 16) / 255)
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
}

/** Ink that reads on the entrant's own color: near-black on light colors, white on dark ones. */
export function inkOn(hex: string): string {
  return luminance(hex) > 0.36 ? "#14161c" : "#ffffff"
}

export function truncate(name: string, max: number): string {
  return name.length > max ? `${name.slice(0, max - 1).trimEnd()}…` : name
}

let probe: SVGTextElement | null = null

/** The name cut to fit `px` in the chip's own type, measured on a hidden SVG text, with an ellipsis when it is cut. */
export function fit(name: string, px: number, weight = 600, size = 17): string {
  if (!probe) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg")
    svg.setAttribute("aria-hidden", "true")
    svg.setAttribute("class", "pointer-events-none fixed -top-96 left-0 size-px overflow-hidden opacity-0")
    probe = document.createElementNS("http://www.w3.org/2000/svg", "text")
    probe.setAttribute("class", "chip-name")
    svg.appendChild(probe)
    document.body.appendChild(svg)
  }
  probe.style.fontWeight = String(weight)
  probe.style.fontSize = `${size}px`
  const width = (text: string) => {
    probe!.textContent = text
    return probe!.getComputedTextLength()
  }
  if (width(name) <= px) return name
  let cut = name
  while (cut.length > 1 && width(`${cut}…`) > px) cut = cut.slice(0, -1)
  return `${cut.trimEnd()}…`
}
