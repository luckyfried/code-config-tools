import { useEffect, useRef } from "react"
import { reducedMotion } from "@/lib/device"

interface StatRollProps {
  value: number
  format: (value: number) => string
  /** Milliseconds before this number starts rolling, so a row of stats lands left to right. */
  delay?: number
}

/** A number that rolls up from zero when the activity opens. */
export function StatRoll({ value, format, delay = 0 }: StatRollProps) {
  const el = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const node = el.current
    if (!node) return
    if (reducedMotion.matches || !Number.isFinite(value)) {
      node.textContent = format(value)
      return
    }
    const duration = 1400
    let frame = 0
    const start = performance.now() + delay
    let shown = ""
    const step = (now: number) => {
      const f = Math.min(1, Math.max(0, (now - start) / duration))
      const eased = 1 - (1 - f) ** 4
      const text = format(value * eased)
      // Only a changed number touches the page, so the last slow digits cost no layout.
      if (text !== shown) node.textContent = shown = text
      if (f < 1) frame = requestAnimationFrame(step)
    }
    node.textContent = format(0)
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [value, format, delay])

  return (
    <span ref={el} className="tabular-nums">
      {format(value)}
    </span>
  )
}
