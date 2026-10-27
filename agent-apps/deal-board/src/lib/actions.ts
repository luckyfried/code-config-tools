import { flushSync } from "react-dom"
import { config } from "@/config"
import { money, when } from "@/lib/format"
import { cardRect, fadeToLost, flyOff, liftOff, travel } from "@/lib/motion"
import { LOST, WON, type Deal, type Move } from "@/lib/pipeline"

/**
 * Commits a change of stage and animates it: a move travels from where the card was to where it lands, a win flies
 * off the right edge, a loss fades into the Lost drawer. `commit` changes what the board shows; `from` is where the
 * card stood when that is not where the board has it (a dragged card, dropped).
 */
export function changeWithMotion(id: string, to: string, commit: () => void, from?: DOMRect) {
  if (to === WON || to === LOST) {
    const lifted = liftOff(id, from)
    flushSync(commit)
    if (to === WON) void flyOff(lifted, confettiColors())
    else void fadeToLost(lifted)
    return
  }
  const first = from ?? cardRect(id)
  flushSync(commit)
  void travel(id, first)
}

function confettiColors() {
  // The stage hues at full chroma and a festive lightness, with the win's green and the theme's amber, so the burst reads as color in either theme.
  const stage = (hex: string) => `oklch(from ${hex} 0.72 calc(c * 1.2) h)`
  return ["var(--won)", ...config.stages.map((s) => stage(s.color)), "var(--age-warm)", "var(--won)", "var(--age-warm)"]
}

const label = (id: string | null) => (id === null ? "" : id === WON ? "Won" : id === LOST ? "Lost" : config.stages.find((s) => s.id === id)?.label ?? id)
const chance = (id: string | null) => config.stages.find((s) => s.id === id)?.probability ?? 0

/** The status line under the headline, the way a person would say it. `at` names the day for a replayed move. */
export function describe(deal: Deal, move: Move, now?: number): string {
  const day = now === undefined ? "" : ` ${when(move.at, now) === "today" || when(move.at, now) === "yesterday" ? when(move.at, now) : `on ${when(move.at, now)}`}`
  if (move.to === WON) return `${deal.company} signed${day}, ${money(deal.value)} won.`
  if (move.to === LOST) return `${deal.company} was lost${day} at ${label(move.from)}.`
  const delta = (deal.value * (chance(move.to) - chance(move.from))) / 100
  if (delta >= 0) return `${deal.company} moved up to ${label(move.to)}${day}, adding ${money(delta)} to the weighted pipeline.`
  return `${deal.company} moved back to ${label(move.to)}${day}, taking ${money(-delta)} off the weighted pipeline.`
}
