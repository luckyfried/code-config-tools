/** The ring curve, cubic-bezier(0.22, 1, 0.36, 1), solved for y at a given x. */
function bezier(x1: number, y1: number, x2: number, y2: number) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by
  const sx = (t: number) => ((ax * t + bx) * t + cx) * t
  const sy = (t: number) => ((ay * t + by) * t + cy) * t
  const dx = (t: number) => (3 * ax * t + 2 * bx) * t + cx
  return (x: number) => {
    if (x <= 0) return 0
    if (x >= 1) return 1
    let t = x
    for (let i = 0; i < 6; i++) {
      const d = dx(t)
      if (Math.abs(d) < 1e-6) break
      t -= (sx(t) - x) / d
    }
    return sy(Math.min(1, Math.max(0, t)))
  }
}

export const ringEase = bezier(0.22, 1, 0.36, 1)
export const RING_MS = 900
export const RING_EASING = "cubic-bezier(0.22, 1, 0.36, 1)"

export const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches

/** Runs onFrame(eased progress) for ms milliseconds; returns a cancel function. */
export function tween(ms: number, onFrame: (k: number) => void, onDone?: () => void) {
  if (prefersReducedMotion() || ms <= 0) {
    onFrame(1)
    onDone?.()
    return () => {}
  }
  let raf = 0
  const start = performance.now()
  const step = (now: number) => {
    const x = Math.min(1, (now - start) / ms)
    onFrame(ringEase(x))
    if (x < 1) raf = requestAnimationFrame(step)
    else onDone?.()
  }
  raf = requestAnimationFrame(step)
  return () => cancelAnimationFrame(raf)
}
