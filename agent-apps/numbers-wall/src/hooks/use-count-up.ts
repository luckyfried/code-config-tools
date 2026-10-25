import { useEffect, type RefObject } from "react"

const DURATION_MS = 1300
const START_MS = 150
const STAGGER_MS = 90

/**
 * Rolls a figure up from zero by writing the element's text directly, so the count costs no React render per frame.
 * The count starts in step with the tile's entrance (--i times 90 ms) and eases out over 1.3 s, so the wall reads as
 * a cascade of numbers climbing. With reveal off, or with reduced motion, the final value is shown at once.
 */
export function useCountUp(
  ref: RefObject<HTMLElement | null>,
  target: number,
  format: (value: number) => string,
  index: number,
  reveal: boolean,
) {
  useEffect(() => {
    const element = ref.current
    if (!element) return
    if (!reveal || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      element.textContent = format(target)
      return
    }
    const start = performance.now() + START_MS + index * STAGGER_MS
    let frame = 0
    element.textContent = format(0)
    const tick = (now: number) => {
      const t = Math.min(1, Math.max(0, (now - start) / DURATION_MS))
      const eased = 1 - Math.pow(1 - t, 3)
      element.textContent = format(t === 1 ? target : target * eased)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(frame)
      element.textContent = format(target)
    }
  }, [ref, target, format, index, reveal])
}
