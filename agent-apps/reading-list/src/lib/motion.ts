// The page's moving parts, on the Web Animations API: the reflow, the fold into the later stack, and the ripple.

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

const EASE_OUT = "cubic-bezier(0.22, 1, 0.36, 1)"
const EASE_IN_OUT = "cubic-bezier(0.65, 0, 0.35, 1)"

export type Snapshot = Map<string, DOMRect>

/** Where every story on the front page is now, so a change can glide from here. */
export function snapshot(root: HTMLElement | null): Snapshot {
  const map: Snapshot = new Map()
  root?.querySelectorAll<HTMLElement>("[data-story]").forEach((el) => map.set(el.dataset.story!, el.getBoundingClientRect()))
  return map
}

/** Glides each story from where it was to where it is: the grid closing a gap, or a story moving to the top. */
export function reflow(root: HTMLElement | null, before: Snapshot) {
  if (!root || reducedMotion()) return
  root.querySelectorAll<HTMLElement>("[data-story]").forEach((el) => {
    const was = before.get(el.dataset.story!)
    const now = el.getBoundingClientRect()
    if (!was) {
      el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 420, easing: EASE_OUT })
      return
    }
    const dx = was.left - now.left
    const dy = was.top - now.top
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
    const sameSize = Math.abs(was.width - now.width) < 2 && Math.abs(was.height - now.height) < 2
    // A story slides only up or down its own column at its own size; any other move would carry it across a
    // neighbor's text, so it fades in where it lands once whatever stood there has gone.
    if (sameSize && Math.abs(dx) < 1) {
      el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "translate(0, 0)" }], {
        duration: 620,
        easing: EASE_IN_OUT,
      })
    } else {
      el.animate([{ opacity: 0 }, { opacity: 0, offset: 0.5, easing: EASE_OUT }, { opacity: 1 }], 880)
    }
  })
}

function copyOf(card: HTMLElement, rect: DOMRect, offset: number) {
  const copy = card.cloneNode(true) as HTMLElement
  copy.removeAttribute("data-story")
  copy.removeAttribute("data-tour")
  copy.removeAttribute("id")
  copy.classList.add("is-copy")
  copy.style.setProperty("--fw", `${rect.width}px`)
  copy.style.setProperty("--fh", `${rect.height}px`)
  copy.style.setProperty("--fy", `${-offset}px`)
  return copy
}

function overlay(className: string, card: HTMLElement, rect: DOMRect) {
  const el = document.createElement("div")
  el.className = className
  el.setAttribute("aria-hidden", "true")
  el.style.setProperty("--x", `${rect.left}px`)
  el.style.setProperty("--y", `${rect.top}px`)
  el.style.setProperty("--w", `${rect.width}px`)
  el.style.setProperty("--h", `${rect.height}px`)
  el.style.setProperty("--topic", card.style.getPropertyValue("--topic"))
  document.body.appendChild(el)
  return el
}

/**
 * Folds a copy of the story in half like a newspaper: the bottom half, picture and type with it, turns back under the
 * top half along a soft crease and never leaves the story's own rectangle; then the folded story slides into the later
 * stack. The story itself leaves the grid at once, so its neighbors close the gap under the fold.
 */
export async function foldIntoStack(card: HTMLElement, stack: HTMLElement | null): Promise<void> {
  if (reducedMotion() || !stack) return
  const rect = card.getBoundingClientRect()
  const fly = overlay("fold-fly", card, rect)
  const top = document.createElement("div")
  top.className = "fold-half fold-top"
  top.appendChild(copyOf(card, rect, 0))
  const crease = document.createElement("div")
  crease.className = "fold-crease"
  top.appendChild(crease)
  const bottom = document.createElement("div")
  bottom.className = "fold-half fold-bottom"
  bottom.appendChild(copyOf(card, rect, rect.height / 2))
  const shade = document.createElement("div")
  shade.className = "fold-shade"
  bottom.appendChild(shade)
  fly.append(top, bottom)

  const turn = { duration: 520, easing: EASE_IN_OUT, fill: "forwards" as const }
  await Promise.all([
    bottom.animate([{ transform: "rotateX(0deg)" }, { transform: "rotateX(-89deg)" }], turn).finished,
    shade.animate([{ opacity: 0 }, { opacity: 1 }], turn).finished,
    crease.animate([{ opacity: 0 }, { opacity: 1 }], turn).finished,
  ])
  bottom.remove()

  const to = stack.getBoundingClientRect()
  const dx = to.left + to.width / 2 - (rect.left + rect.width / 2)
  const dy = to.top + to.height / 2 - (rect.top + rect.height / 4)
  const scale = Math.max(0.08, Math.min(to.height / (rect.height / 2), 0.4))
  await fly.animate(
    [
      { transform: "translate(0, 0) scale(1) rotate(0deg)", opacity: 1 },
      { transform: `translate(${dx}px, ${dy}px) scale(${scale}) rotate(-5deg)`, opacity: 0.7 },
    ],
    { duration: 520, easing: EASE_IN_OUT, fill: "forwards" },
  ).finished
  fly.remove()
  stack.animate(
    [{ transform: "scale(1)" }, { transform: "scale(1.12) rotate(-2deg)" }, { transform: "scale(1)" }],
    { duration: 360, easing: EASE_OUT },
  )
}

/** A copy of a skipped story fades to newsprint grey where it stood, under its neighbors as they slide over the gap. */
export function fadeToNewsprint(card: HTMLElement) {
  if (reducedMotion()) return
  const rect = card.getBoundingClientRect()
  const ghost = overlay("skip-ghost", card, rect)
  ghost.appendChild(copyOf(card, rect, 0))
  ghost
    .animate(
      [
        { filter: "grayscale(0)", opacity: 1, transform: "scale(1)" },
        { filter: "grayscale(1) contrast(0.85) brightness(1.04)", opacity: 0.75, transform: "scale(0.985)", offset: 0.45 },
        { filter: "grayscale(1) contrast(0.8) brightness(1.06)", opacity: 0, transform: "scale(0.95)" },
      ],
      { duration: 440, easing: EASE_IN_OUT, fill: "forwards" },
    )
    .finished.then(() => ghost.remove())
}

/** Sends rings of the topic's color across the page from the story that asked for more like it. */
export function ripple(from: HTMLElement, color: string) {
  if (reducedMotion()) return
  const rect = from.getBoundingClientRect()
  const x = rect.left + rect.width / 2
  const y = rect.top + rect.height / 2
  const reach = Math.hypot(Math.max(x, window.innerWidth - x), Math.max(y, window.innerHeight - y))
  const layer = document.createElement("div")
  layer.className = "ripple-layer"
  layer.setAttribute("aria-hidden", "true")
  layer.style.setProperty("--topic", color)
  document.body.appendChild(layer)
  const rings = [0, 220, 440].map((delay, i) => {
    const ring = document.createElement("div")
    ring.className = i === 0 ? "ripple-ring ripple-fill" : "ripple-ring"
    ring.style.setProperty("--x", `${x}px`)
    ring.style.setProperty("--y", `${y}px`)
    ring.style.setProperty("--d", `${reach * 2}px`)
    layer.appendChild(ring)
    return ring.animate(
      [
        { transform: "translate(-50%, -50%) scale(0.02)", opacity: 1 },
        { transform: "translate(-50%, -50%) scale(0.75)", opacity: 0.9, offset: 0.7 },
        { transform: "translate(-50%, -50%) scale(1)", opacity: 0 },
      ],
      { duration: 1800, delay, easing: "cubic-bezier(0.3, 0.5, 0.4, 1)", fill: "both" },
    ).finished
  })
  Promise.all(rings).then(() => layer.remove())
}
