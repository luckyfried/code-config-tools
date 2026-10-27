import { useEffect, useRef } from "react"
import { reduced } from "@/lib/motion"

// Counts a number up from zero once, after `delay` ms, writing straight to the element so nothing re-renders.
export function useCountUp<T extends HTMLElement>(value: number, format: (n: number) => string, delay: number, run: boolean) {
  const ref = useRef<T>(null)
  const done = useRef(!run)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (done.current || reduced()) {
      el.textContent = format(value)
      return
    }
    done.current = true
    let frame = 0
    const dur = 950
    const t0 = performance.now() + delay
    el.textContent = format(0)
    const step = (t: number) => {
      const k = Math.max(0, Math.min(1, (t - t0) / dur))
      const eased = 1 - Math.pow(1 - k, 3)
      el.textContent = format(value * eased)
      if (k < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => {
      cancelAnimationFrame(frame)
      el.textContent = format(value)
    }
  }, [value, format, delay])
  return ref
}
