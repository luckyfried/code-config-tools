// Card motion through the Web Animations API: transform and opacity only, none of it when the person asks for
// reduced motion.
export const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)"
export const EASE_IN_OUT = "cubic-bezier(0.77, 0, 0.175, 1)"

export const reduced = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches

export function cardEl(id: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(`[data-card="${CSS.escape(id)}"]`)
}

export function snapshot(): Map<string, DOMRect> {
  const rects = new Map<string, DOMRect>()
  document.querySelectorAll<HTMLElement>("[data-card]").forEach((el) => {
    rects.set(el.dataset.card!, el.getBoundingClientRect())
  })
  return rects
}

// A chosen card in the air: a copy of it lifted off the page, flying to wherever the card lands.
export interface Flight {
  ghost: HTMLElement
  from: DOMRect
  action: string
  fromX: number
}

const DRAG_VARS = ["--dx", "--dr", "--reveal-yes", "--reveal-no"]

// Lifts a copy of the card off the page where it is, so the board can move the card itself at once.
export function launch(id: string, action: string, fromX = 0): Flight | null {
  const el = cardEl(id)
  if (!el || reduced()) return null
  for (const v of DRAG_VARS) el.style.removeProperty(v)
  const from = el.getBoundingClientRect()
  const ghost = el.cloneNode(true) as HTMLElement
  for (const a of ["data-card", "data-depth", "data-dragging", "data-returning", "tabindex", "aria-label"]) ghost.removeAttribute(a)
  ghost.classList.remove("card-enter")
  ghost.classList.add("ghost")
  ghost.setAttribute("aria-hidden", "true")
  ghost.style.setProperty("--gx", `${from.left}px`)
  ghost.style.setProperty("--gy", `${from.top}px`)
  ghost.style.setProperty("--gw", `${from.width}px`)
  ghost.style.setProperty("--gh", `${from.height}px`)
  // A card let go mid-swipe keeps the stamp it showed under the finger, only for the first moment of its flight.
  if (fromX !== 0 && (action === "yes" || action === "no")) ghost.style.setProperty(`--reveal-${action}`, "1")
  ghost.style.setProperty("transform", `translateX(${fromX}px) rotate(${fromX / 40}deg)`)
  document.body.append(ghost)
  el.setAttribute("data-launched", "")
  return { ghost, from, action, fromX }
}

// A flight that cannot land (the choice was not taken): the copy goes and the card comes back where it was.
export function abort(flight: Flight | null, id: string) {
  flight?.ghost.remove()
  const el = cardEl(id)
  if (!el) return
  el.removeAttribute("data-launched")
  for (const v of DRAG_VARS) el.style.removeProperty(v)
}

function visible(r: DOMRect | undefined) {
  return !!r && r.width > 0 && r.bottom > 0 && r.top < window.innerHeight
}

// The copy flies in an arc from where the card was to where it is now, or to its column's pile when the card is not
// on screen, turning as it goes, and the card shows under it as it lands.
function fly(flight: Flight, id: string) {
  const { ghost, from, action, fromX } = flight
  const el = cardEl(id)
  if (el?.hasAttribute("data-launched")) return abort(flight, id)
  const list = el?.closest<HTMLElement>(".lane-scroll")
  if (list && list.scrollTop > 0) list.scrollTop = 0
  const at = el?.getBoundingClientRect()
  const pile = visible(at) ? null : document.querySelector<HTMLElement>(`[data-pile="${action}"]`)
  const to = visible(at) ? at! : pile?.getBoundingClientRect()
  const dir = action === "no" ? -1 : 1
  const cx = from.left + from.width / 2
  const cy = from.top + from.height / 2
  let dx: number, dy: number, s: number
  if (to && visible(to)) {
    s = Math.min(1, to.width / from.width)
    dx = to.left + to.width / 2 - cx
    // A card lands top edge to top edge; a pile takes the card into its middle.
    dy = pile ? to.top + to.height / 2 - cy : to.top + (from.height * s) / 2 - cy
  } else {
    s = 0.8
    dx = dir * (window.innerWidth * 0.6 + from.width)
    dy = 80
  }
  const distance = Math.hypot(dx, dy)
  const duration = Math.round(Math.min(860, Math.max(560, 460 + distance * 0.4)))
  const lift = Math.min(110, 36 + distance * 0.1)
  const r0 = fromX / 40
  const air = ghost.animate(
    [
      { transform: `translate(${fromX}px, 0) rotate(${r0}deg) scale(1)`, opacity: 1 },
      { transform: `translate(${fromX + dir * 10}px, -18px) rotate(${r0 + dir * 3}deg) scale(1.04)`, opacity: 1, offset: 0.14 },
      { transform: `translate(${dx * 0.6}px, ${dy * 0.6 - lift}px) rotate(${dir * 9}deg) scale(${(1 + s) / 2 + 0.03})`, opacity: 1, offset: 0.55 },
      { transform: `translate(${dx}px, ${dy}px) rotate(0deg) scale(${s})`, opacity: 1, offset: 0.9 },
      { transform: `translate(${dx}px, ${dy}px) rotate(0deg) scale(${s})`, opacity: 0 },
    ],
    { duration, easing: "cubic-bezier(0.45, 0.05, 0.25, 1)", fill: "forwards" },
  )
  void air.finished.then(() => ghost.remove(), () => ghost.remove())
  ghost.querySelectorAll(".stamp").forEach((stamp) =>
    stamp.animate([{ opacity: 0 }], { duration: Math.min(180, duration * 0.25), easing: EASE_OUT, fill: "forwards" }),
  )
  if (el && !pile) {
    el.animate([{ opacity: 0 }, { opacity: 0, offset: 0.86 }, { opacity: 1 }], { duration })
    el.animate(
      [
        { transform: "translateY(-6px) scale(1.015)" },
        { transform: "translateY(1.5px) scale(0.997)", offset: 0.55 },
        { transform: "none" },
      ],
      { duration: 340, delay: duration * 0.88, easing: EASE_OUT },
    )
  } else if (pile) {
    pile.animate(
      [{ transform: "none" }, { transform: "scale(1.09)", offset: 0.4 }, { transform: "none" }],
      { duration: 360, delay: duration * 0.85, easing: EASE_OUT },
    )
  }
}

// Moves every card from where it was to where it is now. A card in flight lands; one moved without a flight lifts,
// travels, and settles. Cards in the pile of new openings move by their own transitions and are left alone here.
export function flip(before: Map<string, DOMRect>, moved: string | null, flight: Flight | null = null) {
  if (flight && moved) fly(flight, moved)
  if (reduced()) return
  document.querySelectorAll<HTMLElement>("[data-card]").forEach((el) => {
    const id = el.dataset.card!
    if (el.hasAttribute("data-depth") || (flight && id === moved)) return
    const from = before.get(id)
    if (!from) return
    const to = el.getBoundingClientRect()
    const dx = from.left - to.left
    const dy = from.top - to.top
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
    if (id === moved) {
      el.animate(
        [
          { transform: `translate(${dx}px, ${dy}px) scale(1.035) rotate(-1.2deg)`, offset: 0 },
          { transform: `translate(${dx * 0.12}px, ${dy * 0.12 - 14}px) scale(1.03) rotate(0.6deg)`, offset: 0.62 },
          { transform: "translate(0, 2px) scale(0.995)", offset: 0.84 },
          { transform: "none", offset: 1 },
        ],
        { duration: 450, easing: EASE_OUT },
      )
    } else {
      el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], {
        duration: 420,
        easing: EASE_IN_OUT,
      })
    }
  })
}
