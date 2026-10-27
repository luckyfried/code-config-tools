// Card motion through the Web Animations API: transform and opacity only, and none at all when the person asks for
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

// Moves every card from where it was to where it is now; the chosen card lifts, travels, and settles.
export function flip(before: Map<string, DOMRect>, moved: string | null, how: "yes" | "maybe" | null = null) {
  if (reduced()) return
  document.querySelectorAll<HTMLElement>("[data-card]").forEach((el) => {
    const id = el.dataset.card!
    const from = before.get(id)
    if (!from) {
      if (id === moved) el.animate([{ opacity: 0, transform: "scale(0.94)" }, { opacity: 1, transform: "none" }], { duration: 380, easing: EASE_OUT })
      return
    }
    const to = el.getBoundingClientRect()
    const dx = from.left - to.left
    const dy = from.top - to.top
    if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return
    if (id === moved) {
      const tilt = how === "maybe" ? 6 : -2
      if (Math.abs(dx) > 40) {
        travel(el, from, to, tilt)
        return
      }
      el.animate(
        [
          { transform: `translate(${dx}px, ${dy}px) scale(1.04) rotate(0deg)`, zIndex: 30 },
          { transform: `translate(${dx * 0.45}px, ${dy * 0.45 - 40}px) scale(1.06) rotate(${tilt}deg)`, zIndex: 30, offset: 0.5 },
          { transform: `translate(0, 4px) scale(0.99) rotate(${tilt * 0.3}deg)`, zIndex: 30, offset: 0.85 },
          { transform: "none", zIndex: 30 },
        ],
        { duration: 720, easing: EASE_OUT },
      )
      el.querySelector<HTMLElement>("[data-lift]")?.animate([{ opacity: 1 }, { opacity: 1, offset: 0.7 }, { opacity: 0 }], {
        duration: 720,
        easing: "ease-out",
      })
    } else {
      el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], { duration: 480, easing: EASE_IN_OUT })
    }
  })
}

// A card that changes column flies above the board as a copy of itself, since each column scrolls inside its own
// edges; the card waits unseen in its new place until the copy lands on it.
function travel(el: HTMLElement, from: DOMRect, to: DOMRect, tilt: number) {
  const ghost = el.cloneNode(true) as HTMLElement
  ghost.removeAttribute("data-card")
  ghost.classList.remove("card-enter")
  ghost.querySelectorAll<HTMLElement>("*").forEach((n) => (n.style.animation = "none"))
  Object.assign(ghost.style, {
    position: "fixed",
    left: `${to.left}px`,
    top: `${to.top}px`,
    width: `${to.width}px`,
    margin: "0",
    zIndex: "70",
    pointerEvents: "none",
  })
  ;(el.closest(".app") ?? document.body).appendChild(ghost)
  el.style.visibility = "hidden"
  const dx = from.left - to.left
  const dy = from.top - to.top
  const lift = ghost.querySelector<HTMLElement>("[data-lift]")
  if (lift) lift.style.opacity = "1"
  const done = () => {
    ghost.remove()
    el.style.visibility = ""
  }
  ghost
    .animate(
      [
        { transform: `translate(${dx}px, ${dy}px) scale(1.03) rotate(0deg)` },
        { transform: `translate(${dx * 0.45}px, ${dy * 0.45 - 48}px) scale(1.06) rotate(${tilt}deg)`, offset: 0.5 },
        { transform: `translate(0, 4px) scale(0.99) rotate(${tilt * 0.3}deg)`, offset: 0.85 },
        { transform: "none" },
      ],
      { duration: 760, easing: EASE_OUT },
    )
    .finished.then(done, done)
}

// Yes presses a seal into the card's corner before the card moves.
export async function pressSeal(id: string) {
  const seal = cardEl(id)?.querySelector<HTMLElement>("[data-seal]")
  if (!seal || reduced()) return
  seal.style.opacity = "1"
  await seal.animate(
    [
      { transform: "translateZ(40px) scale(2.4) rotate(-28deg)", opacity: 0 },
      { transform: "translateZ(40px) scale(0.86) rotate(-10deg)", opacity: 1, offset: 0.55 },
      { transform: "translateZ(40px) scale(1.05) rotate(-12deg)", opacity: 1, offset: 0.78 },
      { transform: "translateZ(40px) scale(1) rotate(-12deg)", opacity: 1 },
    ],
    { duration: 520, easing: EASE_OUT },
  ).finished
  seal.style.opacity = ""
}

// No slides the card out to the left.
export async function slideOut(id: string) {
  const el = cardEl(id)
  if (!el || reduced()) return
  await el.animate(
    [
      { transform: "none", opacity: 1 },
      { transform: "translateX(-24px) rotate(1deg)", opacity: 1, offset: 0.2 },
      { transform: "translateX(-115%) rotate(-7deg)", opacity: 0 },
    ],
    { duration: 520, easing: "cubic-bezier(0.55, 0, 0.75, 0.2)", fill: "forwards" },
  ).finished
}

// Maybe tips the card before it drops onto the pile.
export async function tipCard(id: string) {
  const el = cardEl(id)
  if (!el || reduced()) return
  await el.animate([{ transform: "none" }, { transform: "rotate(-5deg) translateY(-10px) scale(1.02)" }], {
    duration: 240,
    easing: EASE_OUT,
    fill: "forwards",
  }).finished
}

// On a phone a chosen card leaves the list it is in: right for yes, left for no, up for maybe.
export async function leaveList(id: string, action: string, from = { x: 0, y: 0 }) {
  const el = cardEl(id)
  if (!el || reduced()) return
  const w = el.offsetWidth
  const end =
    action === "yes"
      ? `translate(${w * 1.2}px, ${from.y}px) rotate(12deg)`
      : action === "no"
        ? `translate(${-w * 1.2}px, ${from.y}px) rotate(-12deg)`
        : `translate(${from.x}px, -60%) rotate(-6deg) scale(0.9)`
  await el.animate(
    [
      { transform: `translate(${from.x}px, ${from.y}px) rotate(${from.x / 24}deg)`, opacity: 1 },
      { transform: end, opacity: 0 },
    ],
    { duration: 300, easing: EASE_OUT, fill: "forwards" },
  ).finished
}

// A card flies from the board into the compare tray as a small copy of its photo.
export async function flyTo(id: string, slot: Element | null) {
  const el = cardEl(id)
  const photo = el?.querySelector<HTMLElement>("[data-photo]")
  if (!photo || !slot || reduced()) return
  const a = photo.getBoundingClientRect()
  const b = slot.getBoundingClientRect()
  const ghost = photo.cloneNode(true) as HTMLElement
  Object.assign(ghost.style, {
    position: "fixed",
    left: `${a.left}px`,
    top: `${a.top}px`,
    width: `${a.width}px`,
    height: `${a.height}px`,
    zIndex: "80",
    pointerEvents: "none",
    borderRadius: "16px",
    overflow: "hidden",
    boxShadow: "0 30px 60px -20px rgb(0 0 0 / 45%)",
    transformOrigin: "top left",
  })
  document.body.appendChild(ghost)
  const sx = b.width / a.width
  const sy = b.height / a.height
  await ghost.animate(
    [
      { transform: "none", opacity: 1 },
      { transform: `translate(${(b.left - a.left) * 0.5}px, ${(b.top - a.top) * 0.5 - 80}px) scale(${(1 + sx) / 2}, ${(1 + sy) / 2}) rotate(-4deg)`, opacity: 1, offset: 0.5 },
      { transform: `translate(${b.left - a.left}px, ${b.top - a.top}px) scale(${sx}, ${sy})`, opacity: 1 },
    ],
    { duration: 640, easing: EASE_IN_OUT },
  ).finished
  ghost.remove()
}

// The pointer tilt: the card leans a few degrees toward the pointer and the layers on it part in depth.
export function tilt(el: HTMLElement, x: number, y: number) {
  el.style.setProperty("--ry", `${(x - 0.5) * 12}deg`)
  el.style.setProperty("--rx", `${(0.5 - y) * 10}deg`)
  el.style.setProperty("--gx", `${x * 100}%`)
  el.style.setProperty("--gy", `${y * 100}%`)
}

export function untilt(el: HTMLElement) {
  el.style.setProperty("--ry", "0deg")
  el.style.setProperty("--rx", "0deg")
}

// The tilt played once on its own so the depth shows without a pointer.
export function tiltShow(id: string): Promise<void> {
  const el = cardEl(id)
  if (!el || reduced()) return Promise.resolve()
  el.dataset.tilting = ""
  const start = performance.now()
  const dur = 1500
  return new Promise((done) => {
    const step = (t: number) => {
      const k = Math.min(1, (t - start) / dur)
      const a = k * Math.PI * 2
      const amp = Math.sin(k * Math.PI)
      tilt(el, 0.5 + Math.cos(a) * 0.5 * amp, 0.5 + Math.sin(a) * 0.45 * amp)
      if (k < 1) requestAnimationFrame(step)
      else {
        untilt(el)
        delete el.dataset.tilting
        done()
      }
    }
    requestAnimationFrame(step)
  })
}
