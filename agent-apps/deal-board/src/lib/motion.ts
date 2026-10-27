// The board's motion: a card traveling between stages, a win flying off the right edge with confetti along its
// line, a loss fading out where it stood while the Lost drawer's handle answers. Each works on a copy of the card in
// a fixed layer above the page, so a column's scrolling never clips a move or a win; a loss is clipped to its own
// column. Each finishes instantly when the person prefers reduced motion.

export const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)"
export const EASE_IN_OUT = "cubic-bezier(0.77, 0, 0.175, 1)"

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

const cards = new Map<string, HTMLElement>()
const targets = new Map<string, HTMLElement>()

/** A ref for a card on the board, so a move can find where the card is and where it lands. */
export function cardRef(id: string) {
  return (el: HTMLElement | null) => {
    if (!el) return
    cards.set(id, el)
    return () => {
      if (cards.get(id) === el) cards.delete(id)
    }
  }
}

/** A ref for something a closed deal travels toward: "lost" (the Lost drawer's handle) or "won". */
export function targetRef(name: string) {
  return (el: HTMLElement | null) => {
    if (!el) return
    targets.set(name, el)
    return () => {
      if (targets.get(name) === el) targets.delete(name)
    }
  }
}

const visible = (el: HTMLElement) => el.getClientRects().length > 0 && el.offsetParent !== null

export const cardRect = (id: string) => cards.get(id)?.getBoundingClientRect()

function layer(): HTMLElement {
  let fx = document.getElementById("fx")
  if (!fx) {
    fx = document.createElement("div")
    fx.id = "fx"
    fx.setAttribute("aria-hidden", "true")
    document.body.appendChild(fx)
  }
  return fx
}

function place(el: HTMLElement, rect: DOMRect) {
  el.style.position = "fixed"
  el.style.left = "0px"
  el.style.top = "0px"
  el.style.width = `${rect.width}px`
  el.style.height = `${rect.height}px`
  el.style.margin = "0"
  el.style.transform = `translate(${rect.left}px, ${rect.top}px)`
}

/** A copy of a card standing where `rect` is, above everything. */
function ghostOf(el: HTMLElement, rect: DOMRect): HTMLElement {
  const ghost = el.cloneNode(true) as HTMLElement
  ghost.removeAttribute("id")
  ghost.removeAttribute("data-deal")
  ghost.style.opacity = "1"
  const face = ghost.querySelector<HTMLElement>(".deal-face")
  if (face) face.style.boxShadow = "var(--lift-shadow)"
  place(ghost, rect)
  layer().appendChild(ghost)
  return ghost
}

const at = (rect: DOMRect, scale = 1, turn = 0) => `translate(${rect.left}px, ${rect.top}px) scale(${scale}) rotate(${turn}deg)`

/**
 * Moves the card `id` from `first` to wherever it now sits: call it after the board has re-rendered the card in its
 * new stage. A trip to another stage is a flight: the card lifts and tilts toward where it is going, arcs over the
 * board with two fading afterimages behind it, lands with a small squash, and its new column glows in its color. A
 * short trip (a dropped card settling into place) eases out without the arc.
 */
export async function travel(id: string, first: DOMRect | undefined) {
  const el = cards.get(id)
  if (!el || !first || reducedMotion()) return
  const last = el.getBoundingClientRect()
  const dx = last.left - first.left
  const dy = last.top - first.top
  const distance = Math.hypot(dx, dy)
  if (distance < 2) return
  el.style.transition = "none"
  el.style.opacity = "0"
  const flights: Animation[] = []
  const ghosts: HTMLElement[] = []
  if (distance <= 160) {
    const ghost = ghostOf(el, last)
    ghosts.push(ghost)
    flights.push(ghost.animate([{ transform: at(first, 1.035, -0.8) }, { transform: at(last) }], { duration: 300, easing: EASE_OUT }))
  } else {
    const frames = arc(first, last, distance)
    const duration = Math.min(950, 760 + distance * 0.3)
    // The afterimages first, so the card itself flies above them.
    for (const [delay, opacity] of [
      [70, 0.2],
      [35, 0.38],
    ] as const) {
      const trail = ghostOf(el, last)
      trail.style.opacity = "0"
      ghosts.push(trail)
      const faded = frames.map((frame, i) => ({ ...frame, opacity: i === 0 || i === frames.length - 1 ? 0 : opacity }))
      flights.push(trail.animate(faded, { duration, delay, easing: "linear", fill: "both" }))
    }
    const ghost = ghostOf(el, last)
    ghosts.push(ghost)
    flights.push(ghost.animate(frames, { duration, easing: "linear" }))
  }
  try {
    await flights[flights.length - 1].finished
  } finally {
    for (const ghost of ghosts) ghost.remove()
    el.style.opacity = ""
    el.style.transition = ""
    if (distance > 160) land(el)
  }
}

/** The keyframes of a flight from `first` to `last`: a lift in place, an arc whose height grows with the distance, and a squash on landing. */
function arc(first: DOMRect, last: DOMRect, distance: number): Keyframe[] {
  const lift = Math.min(150, 46 + distance * 0.22)
  const tilt = Math.sign(last.left - first.left || 1) * 4
  const peakX = (first.left + last.left) / 2
  const peakY = Math.min(first.top, last.top) - lift
  const point = (t: number) => {
    const u = 1 - t
    return new DOMRect(u * u * first.left + 2 * u * t * peakX + t * t * last.left, u * u * first.top + 2 * u * t * peakY + t * t * last.top, last.width, last.height)
  }
  const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2)
  const frames: Keyframe[] = [
    { offset: 0, transform: at(first, 1, 0) },
    { offset: 0.12, transform: at(new DOMRect(first.left, first.top - 8, first.width, first.height), 1.07, -tilt * 0.5), easing: "linear" },
  ]
  const steps = 14
  for (let k = 1; k <= steps; k++) {
    const t = k / steps
    const s = ease(t)
    const turn = tilt * Math.sin(Math.PI * s)
    frames.push({ offset: 0.12 + 0.72 * t, transform: at(point(s), 1.07 - 0.07 * s * s, turn) })
  }
  frames.push({ offset: 0.92, transform: `${at(last)} scale(1.025, 0.965)` })
  frames.push({ offset: 1, transform: at(last) })
  return frames
}

/** The column a card lands in glows once in its stage's color. */
function land(el: HTMLElement) {
  el.animate([{ transform: "scale(1.02)" }, { transform: "none" }], { duration: 260, easing: EASE_OUT })
  const column = el.closest<HTMLElement>(".stage-column")
  if (!column) return
  column.animate(
    [
      { boxShadow: "inset 0 0 0 2px color-mix(in oklab, var(--stage) 80%, transparent), inset 0 0 48px color-mix(in oklab, var(--stage) 22%, transparent)" },
      { boxShadow: "inset 0 0 0 2px color-mix(in oklab, var(--stage) 0%, transparent), inset 0 0 48px color-mix(in oklab, var(--stage) 0%, transparent)" },
    ],
    { duration: 700, easing: "ease-out" },
  )
}

/** A copy of the card `id` taken before it leaves the board, for `flyOff` or `fadeToLost` to animate; `lane` is the part of its column it shows in. */
export function liftOff(id: string, from?: DOMRect) {
  const el = cards.get(id)
  const rect = from ?? el?.getBoundingClientRect()
  if (!el || !rect || !visible(el)) return null
  const lane = el.closest<HTMLElement>("[data-lane]")?.getBoundingClientRect() ?? null
  return { ghost: ghostOf(el, rect), rect, lane }
}

/** A win: the card leaves off the right edge, and confetti bursts along the line it travels. */
export async function flyOff(lifted: ReturnType<typeof liftOff>, colors: string[]) {
  if (!lifted) return
  const { ghost, rect } = lifted
  if (reducedMotion()) {
    await ghost.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 200, easing: "ease" }).finished.catch(() => {})
    ghost.remove()
    return
  }
  const width = window.innerWidth
  const end = new DOMRect(width + 48, rect.top - 18, rect.width, rect.height)
  const duration = 760
  const flight = ghost.animate(
    [
      { transform: at(rect) },
      { transform: at(new DOMRect(rect.left - 10, rect.top + 2, rect.width, rect.height), 1.04, -2), offset: 0.16 },
      { transform: at(end, 1, 5) },
    ],
    { duration, easing: "cubic-bezier(0.5, 0, 0.75, 0.2)", fill: "forwards" },
  )
  confettiAlong(rect, width, colors, duration)
  await flight.finished.catch(() => {})
  ghost.remove()
}

function confettiAlong(rect: DOMRect, width: number, colors: string[], duration: number) {
  const fx = layer()
  const y = rect.top + rect.height / 2
  const startX = rect.left + rect.width * 0.5
  const span = Math.max(120, width - startX)
  const count = Math.round(Math.min(110, Math.max(56, span / 7)))
  for (let i = 0; i < count; i++) {
    const t = i / (count - 1)
    const x = startX + span * t
    const piece = document.createElement("span")
    piece.className = "confetti"
    piece.style.background = colors[i % colors.length]
    const w = 8 + ((i * 7) % 6)
    const h = i % 3 === 0 ? w : w * 1.8
    piece.style.width = `${w}px`
    piece.style.height = `${h}px`
    piece.style.borderRadius = i % 4 === 0 ? "999px" : "2px"
    piece.style.left = `${x}px`
    piece.style.top = `${y}px`
    fx.appendChild(piece)
    // The card passes this point along an accelerating path, so the burst follows it outward, then the pieces hang
    // in the air and fall, long enough to be seen.
    const delay = duration * (0.12 + 0.6 * Math.sqrt(t))
    const spread = 50 + ((i * 37) % 120)
    const dy = (i % 2 === 0 ? -1 : 1) * spread
    const dx = ((i * 53) % 90) - 20
    const spin = ((i * 97) % 720) - 360
    piece
      .animate(
        [
          { transform: "translate(-50%, -50%) scale(0.4) rotate(0deg)", opacity: 0 },
          { transform: "translate(-50%, -50%) scale(1) rotate(0deg)", opacity: 1, offset: 0.06 },
          { transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) rotate(${spin * 0.6}deg)`, opacity: 1, offset: 0.35 },
          { transform: `translate(calc(-50% + ${dx * 1.4}px), calc(-50% + ${dy * 0.8 + 70}px)) rotate(${spin}deg)`, opacity: 1, offset: 0.8 },
          { transform: `translate(calc(-50% + ${dx * 1.5}px), calc(-50% + ${dy * 0.8 + 110}px)) rotate(${spin * 1.2}deg)`, opacity: 0 },
        ],
        { duration: 2200, delay, easing: EASE_OUT, fill: "both" },
      )
      .finished.catch(() => {})
      .finally(() => piece.remove())
  }
}

/** A loss: the card greys and fades out where it stood, clipped to its own column, and the Lost drawer's handle answers. */
export async function fadeToLost(lifted: ReturnType<typeof liftOff>) {
  if (!lifted) return
  const { ghost, rect, lane } = lifted
  const target = targets.get("lost")
  if (lane) {
    const inset = [lane.top - rect.top, rect.right - lane.right, rect.bottom - lane.bottom, lane.left - rect.left].map((n) => `${Math.max(0, n)}px`)
    ghost.style.clipPath = `inset(${inset.join(" ")})`
  }
  if (reducedMotion()) {
    await ghost.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 200, easing: "ease" }).finished.catch(() => {})
  } else {
    await ghost
      .animate(
        [
          { transform: at(rect), opacity: 1, filter: "saturate(1)" },
          { transform: at(rect, 0.98), opacity: 0.6, filter: "saturate(0)", offset: 0.35 },
          { transform: at(rect, 0.94), opacity: 0, filter: "saturate(0)" },
        ],
        { duration: 420, easing: EASE_OUT, fill: "forwards" },
      )
      .finished.catch(() => {})
  }
  ghost.remove()
  if (target && onScreen(target)) answer(target)
}

const onScreen = (el: HTMLElement) => {
  if (!visible(el)) return false
  const r = el.getBoundingClientRect()
  return r.right > 0 && r.left < window.innerWidth && r.bottom > 0 && r.top < window.innerHeight
}

/** A small nod from the thing that just received a deal. */
export function answer(el: HTMLElement | undefined) {
  if (!el || reducedMotion()) return
  el.animate([{ transform: "scale(1)" }, { transform: "scale(1.06)" }, { transform: "scale(1)" }], { duration: 300, easing: EASE_OUT })
}

export const target = (name: string) => targets.get(name)
