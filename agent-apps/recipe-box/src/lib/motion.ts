// Card motion through the Web Animations API, each one shortened to nothing when the person asks for reduced motion.
export const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)"
export const EASE_IN_OUT = "cubic-bezier(0.77, 0, 0.175, 1)"

export const reduced = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches

export const cardEl = (id: string) => document.querySelector<HTMLElement>(`[data-card="${CSS.escape(id)}"]`)
const slotTarget = (day: string) =>
  document.querySelector<HTMLElement>(`[data-slot="${day}"] [data-slot-target]`)

const finished = (a: Animation) => a.finished.then(() => undefined, () => undefined)

// "This week": the card dips, and a round copy of its photo lifts off, shrinks, and arcs into the day's slot, where the
// slot's own dish lands with a soft bounce. The flight moves by transform and opacity alone.
export async function flyToSlot(id: string, day: string, image: string, color: string): Promise<void> {
  const card = cardEl(id)
  const photo = card?.querySelector<HTMLElement>(".photo")
  const slot = slotTarget(day)
  if (!card || !photo || !slot || reduced()) return
  const strip = document.querySelector<HTMLElement>(".strip")
  const floor = strip ? strip.getBoundingClientRect().top : window.innerHeight
  const from = photo.getBoundingClientRect()
  const to = slot.getBoundingClientRect()
  // A card scrolled out of view starts its flight from the nearest visible edge of the box.
  const size = Math.min(from.width, from.height, floor * 0.4)
  const top = Math.min(Math.max(from.top + from.height / 2 - size / 2, 0), floor - size)
  const ghost = document.createElement("div")
  ghost.className = "drag-ghost"
  ghost.style.cssText = `left:0;top:0;width:${size}px;height:${size}px;border-radius:50%;background:${color}`
  const img = document.createElement("img")
  img.src = image
  img.alt = ""
  img.style.cssText = "width:100%;height:100%;object-fit:cover;display:block"
  ghost.append(img)
  document.body.append(ghost)
  card.animate(
    [{ transform: "none" }, { transform: "scale(0.93)", offset: 0.35 }, { transform: "none" }],
    { duration: 520, easing: EASE_OUT },
  )
  const x0 = from.left + from.width / 2
  const y0 = top + size / 2
  const x2 = to.left + to.width / 2
  const y2 = to.top + to.height / 2
  const x1 = (x0 + x2) / 2 + (x2 > x0 ? -60 : 60)
  const y1 = Math.min(y0, y2) - Math.max(120, Math.abs(x2 - x0) * 0.25)
  const end = to.width / size
  const frames: Keyframe[] = []
  const steps = 14
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const e = 1 - Math.pow(1 - t, 2.2)
    const x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * x1 + t * t * x2
    const y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * y1 + t * t * y2
    const k = 1 + (end - 1) * e
    frames.push({ transform: `translate(${x - size / 2}px, ${y - size / 2}px) scale(${k}) rotate(${(1 - t) * -6}deg)` })
  }
  await finished(ghost.animate(frames, { duration: 760, easing: "cubic-bezier(0.45, 0.05, 0.35, 1)", fill: "forwards" }))
  ghost.remove()
}

// "Keep": a small nod.
export function nod(id: string) {
  const el = cardEl(id)
  if (!el || reduced()) return
  el.animate(
    [
      { transform: "none" },
      { transform: "translateY(-5px) rotate(-2.2deg)", offset: 0.25 },
      { transform: "translateY(1px) rotate(1.6deg)", offset: 0.55 },
      { transform: "rotate(-0.6deg)", offset: 0.8 },
      { transform: "none" },
    ],
    { duration: 620, easing: EASE_OUT },
  )
}

// "Skip": the card folds away before it leaves the box.
export async function foldAway(id: string): Promise<void> {
  const el = cardEl(id)
  if (!el || reduced()) return
  el.style.transformOrigin = "50% 0"
  await finished(
    el.animate(
      [
        { transform: "perspective(700px) rotateX(0) scaleY(1)", opacity: 1 },
        { transform: "perspective(700px) rotateX(-28deg) scaleY(0.82)", opacity: 1, offset: 0.4 },
        { transform: "perspective(700px) rotateX(-88deg) scaleY(0.3)", opacity: 0 },
      ],
      { duration: 460, easing: EASE_IN_OUT, fill: "forwards" },
    ),
  )
}
