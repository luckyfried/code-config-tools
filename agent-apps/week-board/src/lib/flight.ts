/** Card flights: a fixed copy of a card floats above the board, so no column's scroll box clips it, while the
 * real card holds its slot hidden underneath and shows again when the copy lands. */

export const EASE_OUT = "cubic-bezier(0.16, 1, 0.3, 1)"
export const EASE_MOVE = "cubic-bezier(0.65, 0, 0.35, 1)"

export const cardNode = (id: string) => document.querySelector<HTMLElement>(`[data-flip-id="${id}"]`)

/** The first box of a list of selectors that is on screen (a phone hides the rails, a computer hides the day strip). */
export function visibleRect(...selectors: string[]): DOMRect | null {
  for (const s of selectors) {
    const r = document.querySelector(s)?.getBoundingClientRect()
    if (r && r.width > 0 && r.height > 0) return r
  }
  return null
}

export interface Ghost {
  root: HTMLElement
  card: HTMLElement
  rect: DOMRect
  remove: () => void
}

/** Copies a card into a fixed layer over the board at the card's place and hides the real one. */
export function ghostOf(real: HTMLElement): Ghost {
  const rect = real.getBoundingClientRect()
  const copy = real.cloneNode(true) as HTMLElement
  for (const n of [copy, ...copy.querySelectorAll<HTMLElement>("*")]) {
    n.removeAttribute("data-flip-id")
    n.removeAttribute("data-card-id")
    n.removeAttribute("id")
    n.classList.remove("wb-enter", "wb-carry-in")
    n.style.removeProperty("transform")
    n.style.removeProperty("transition")
  }
  const root = document.createElement("div")
  root.className = "wb-ghost"
  root.setAttribute("aria-hidden", "true")
  root.inert = true
  root.style.setProperty("left", `${rect.left}px`)
  root.style.setProperty("top", `${rect.top}px`)
  root.style.setProperty("width", `${rect.width}px`)
  root.appendChild(copy)
  document.body.appendChild(root)
  real.style.setProperty("visibility", "hidden")
  return {
    root,
    card: copy.querySelector<HTMLElement>(".wb-card") ?? copy,
    rect,
    remove: () => root.remove(),
  }
}

export const reveal = (id: string) => cardNode(id)?.style.removeProperty("visibility")

/** Holds the cards of one column where they were for `ms`, so the slot they open arrives with the card. */
export function delaySlot(day: string, ms: number) {
  document.querySelectorAll<HTMLElement>(`[id="day-${day}"] [data-flip-id]`).forEach((n) =>
    n.getAnimations().forEach((a) => a.effect?.updateTiming({ delay: ms, fill: "backwards" })),
  )
}

/** A card that grows out of a small mark (a day's stub on the rail, or its pill in the day strip) into its slot. */
export function flyIn(real: HTMLElement, from: DOMRect, ms: number): Promise<void> {
  const g = ghostOf(real)
  const dx = from.left + from.width / 2 - (g.rect.left + g.rect.width / 2)
  const dy = from.top + from.height / 2 - (g.rect.top + g.rect.height / 2)
  const s = Math.min(0.9, Math.max(0.35, from.width / g.rect.width))
  const a = g.root.animate(
    [
      { transform: `translate(${dx}px, ${dy}px) scale(${s}) rotate(-4deg)`, opacity: 0 },
      { opacity: 1, offset: 0.25 },
      { transform: "none", opacity: 1 },
    ],
    { duration: ms, easing: EASE_OUT, fill: "forwards" },
  )
  return a.finished.then(() => {
    real.style.removeProperty("visibility")
    g.remove()
  }, () => {
    real.style.removeProperty("visibility")
    g.remove()
  })
}
