import { useEffect, useRef } from "react"

type Swipe = "yes" | "no" | "maybe"

// Swipes on a phone card: right for yes, left for no. Up for maybe starts with a short hold, so an ordinary upward
// flick still scrolls the board.
export function useSwipe<T extends HTMLElement>(on: boolean, onSwipe: (action: Swipe, from: { x: number; y: number }) => void) {
  const ref = useRef<T>(null)
  const cb = useRef(onSwipe)
  useEffect(() => {
    cb.current = onSwipe
  })
  useEffect(() => {
    const el = ref.current
    if (!el || !on) return
    let x0 = 0
    let y0 = 0
    let mode: "idle" | "h" | "hold" | "scroll" = "idle"
    let timer = 0
    let dx = 0
    let dy = 0
    const set = (x: number, y: number) => {
      el.style.setProperty("--dx", `${x}px`)
      el.style.setProperty("--dy", `${y}px`)
      el.style.setProperty("--dr", `${x / 22}deg`)
      el.style.setProperty("--reveal-yes", `${Math.max(0, Math.min(1, x / 110))}`)
      el.style.setProperty("--reveal-no", `${Math.max(0, Math.min(1, -x / 110))}`)
      el.style.setProperty("--reveal-maybe", `${Math.max(0, Math.min(1, -y / 90))}`)
    }
    const reset = () => {
      window.clearTimeout(timer)
      delete el.dataset.held
      delete el.dataset.dragging
      el.dataset.returning = ""
      set(0, 0)
      window.setTimeout(() => delete el.dataset.returning, 260)
      mode = "idle"
    }
    const start = (e: TouchEvent) => {
      if (e.touches.length !== 1 || (e.target as Element).closest("button, a, textarea, input")) {
        mode = "scroll"
        return
      }
      x0 = e.touches[0].clientX
      y0 = e.touches[0].clientY
      dx = dy = 0
      mode = "idle"
      timer = window.setTimeout(() => {
        if (mode !== "idle") return
        mode = "hold"
        el.dataset.held = ""
        el.dataset.dragging = ""
      }, 260)
    }
    const move = (e: TouchEvent) => {
      if (mode === "scroll") return
      dx = e.touches[0].clientX - x0
      dy = e.touches[0].clientY - y0
      if (mode === "idle") {
        if (Math.abs(dx) > 10 && Math.abs(dx) > Math.abs(dy)) {
          mode = "h"
          window.clearTimeout(timer)
          el.dataset.dragging = ""
        } else if (Math.abs(dy) > 10) {
          mode = "scroll"
          window.clearTimeout(timer)
          return
        } else return
      }
      e.preventDefault()
      set(dx, mode === "hold" ? Math.min(0, dy) : 0)
    }
    const end = () => {
      if (mode === "scroll" || mode === "idle") {
        window.clearTimeout(timer)
        mode = "idle"
        return
      }
      const from = { x: dx, y: mode === "hold" ? Math.min(0, dy) : 0 }
      const pick: Swipe | null =
        mode === "hold" && dy < -90 && Math.abs(dy) > Math.abs(dx) ? "maybe" : dx > 110 ? "yes" : dx < -110 ? "no" : null
      if (pick) {
        window.clearTimeout(timer)
        delete el.dataset.held
        delete el.dataset.dragging
        mode = "idle"
        cb.current(pick, from)
        window.setTimeout(reset, 400)
      } else reset()
    }
    el.addEventListener("touchstart", start, { passive: true })
    el.addEventListener("touchmove", move, { passive: false })
    el.addEventListener("touchend", end)
    el.addEventListener("touchcancel", reset)
    return () => {
      window.clearTimeout(timer)
      el.removeEventListener("touchstart", start)
      el.removeEventListener("touchmove", move)
      el.removeEventListener("touchend", end)
      el.removeEventListener("touchcancel", reset)
    }
  }, [on])
  return ref
}
