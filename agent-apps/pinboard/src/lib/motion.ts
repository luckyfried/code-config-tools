/** The wall's motion, through the Web Animations API. Every helper is a no-op when the person asks for less motion. */

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

const SETTLE = "cubic-bezier(0.22, 1, 0.36, 1)"

/** A card arriving: a short lift from below, then it settles. */
export function arrive(el: HTMLElement, delay: number) {
  if (reducedMotion()) return
  el.animate(
    [
      { opacity: 0, transform: "translateY(18px) scale(0.97)" },
      { opacity: 1, transform: "translateY(-3px) scale(1.005)", offset: 0.7 },
      { opacity: 1, transform: "translateY(0) scale(1)" },
    ],
    { duration: 520, delay, easing: SETTLE, fill: "backwards" },
  )
}

/** Keep: a small nod. */
export function nod(el: HTMLElement) {
  if (reducedMotion()) return
  el.animate(
    [
      { transform: "rotate(0deg) scale(1)" },
      { transform: "rotate(-2.2deg) scale(1.03)", offset: 0.3 },
      { transform: "rotate(1.4deg) scale(1.01)", offset: 0.6 },
      { transform: "rotate(0deg) scale(1)" },
    ],
    { duration: 460, easing: "ease-out" },
  )
}

/** The kept mark popping onto the card. */
export function pop(el: HTMLElement) {
  if (reducedMotion()) return
  el.animate(
    [
      { transform: "scale(0)", opacity: 0 },
      { transform: "scale(1.35)", opacity: 1, offset: 0.6 },
      { transform: "scale(1)", opacity: 1 },
    ],
    { duration: 380, easing: "ease-out" },
  )
}

/** Set aside: the card folds away from its top edge. Resolves when it is gone. */
export function fold(el: HTMLElement): Promise<void> {
  if (reducedMotion()) return Promise.resolve()
  const animation = el.animate(
    [
      { transform: "perspective(900px) rotateX(0deg) scale(1)", opacity: 1, transformOrigin: "50% 0%" },
      { transform: "perspective(900px) rotateX(-12deg) scale(0.96)", opacity: 0.9, offset: 0.35, transformOrigin: "50% 0%" },
      { transform: "perspective(900px) rotateX(-80deg) scale(0.85)", opacity: 0, transformOrigin: "50% 0%" },
    ],
    { duration: 420, easing: "ease-in", fill: "forwards" },
  )
  return animation.finished.then(() => undefined, () => undefined)
}

/** Move: a copy of the card flies to its board's shelf and shrinks into it; the shelf takes a small bump. */
export function flyTo(card: HTMLElement, shelf: HTMLElement | null): Promise<void> {
  if (reducedMotion() || !shelf) return Promise.resolve()
  const from = card.getBoundingClientRect()
  const to = shelf.getBoundingClientRect()
  const ghost = card.cloneNode(true) as HTMLElement
  ghost.setAttribute("aria-hidden", "true")
  ghost.classList.add("pointer-events-none", "fixed", "z-50", "m-0")
  ghost.style.setProperty("left", `${from.left}px`)
  ghost.style.setProperty("top", `${from.top}px`)
  ghost.style.setProperty("width", `${from.width}px`)
  document.body.appendChild(ghost)
  const dx = to.left + to.width / 2 - (from.left + from.width / 2)
  const dy = to.top + to.height / 2 - (from.top + from.height / 2)
  const scale = Math.max(0.08, Math.min(0.2, to.height / from.height))
  const flight = ghost.animate(
    [
      { transform: "translate(0, 0) scale(1) rotate(0deg)", opacity: 1 },
      { transform: `translate(${dx * 0.45}px, ${dy * 0.45 - 40}px) scale(0.6) rotate(-4deg)`, opacity: 1, offset: 0.45 },
      { transform: `translate(${dx}px, ${dy}px) scale(${scale}) rotate(0deg)`, opacity: 0.2 },
    ],
    { duration: 720, easing: "cubic-bezier(0.5, 0, 0.2, 1)", fill: "forwards" },
  )
  return flight.finished.then(
    () => {
      ghost.remove()
      shelf.animate(
        [{ transform: "scale(1)" }, { transform: "scale(1.12)", offset: 0.4 }, { transform: "scale(1)" }],
        { duration: 340, easing: "ease-out" },
      )
    },
    () => ghost.remove(),
  )
}

/** Where each card sits inside `wall`, so scrolling between two measures changes nothing. */
export function measure(wall: HTMLElement, cards: Map<string, HTMLElement>) {
  const origin = wall.getBoundingClientRect()
  const at = new Map<string, { x: number; y: number }>()
  for (const [id, el] of cards) {
    const box = el.getBoundingClientRect()
    at.set(id, { x: box.left - origin.left, y: box.top - origin.top })
  }
  return at
}

/** Animates every card from where it was to where the new layout put it. */
export function flip(wall: HTMLElement, cards: Map<string, HTMLElement>, before: Map<string, { x: number; y: number }>) {
  const after = measure(wall, cards)
  if (!reducedMotion()) {
    for (const [id, el] of cards) {
      const was = before.get(id)
      const now = after.get(id)
      if (!was || !now) continue
      const dx = was.x - now.x
      const dy = was.y - now.y
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) continue
      el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "translate(0, 0)" }], {
        duration: 480,
        easing: SETTLE,
      })
    }
  }
  return after
}
