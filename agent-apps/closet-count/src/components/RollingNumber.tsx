import { useEffect, useRef, useState } from "react"
import { useReducedMotion } from "@/hooks/use-media"

/**
 * A number that rolls to its value in tabular figures: from `from` on first show, then from the last value on every
 * change, so a new wear visibly lowers a cost per wear.
 */
export function RollingNumber({
  value,
  from,
  format,
  delay = 0,
  duration = 1100,
  className,
}: {
  value: number
  from?: number
  format: (n: number) => string
  delay?: number
  duration?: number
  className?: string
}) {
  const reduced = useReducedMotion()
  const [shown, setShown] = useState(reduced ? value : (from ?? value))
  const last = useRef(shown)

  useEffect(() => {
    const start = last.current
    if (reduced || start === value) {
      last.current = value
      setShown(value)
      return
    }
    let frame = 0
    let t0 = 0
    const tick = (now: number) => {
      if (!t0) t0 = now
      const p = Math.min(1, Math.max(0, (now - t0 - delay) / duration))
      const eased = 1 - Math.pow(1 - p, 4)
      const v = start + (value - start) * eased
      last.current = v
      setShown(v)
      if (p < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [value, reduced, delay, duration])

  return <span className={className} style={{ fontVariantNumeric: "tabular-nums" }}>{format(shown)}</span>
}
