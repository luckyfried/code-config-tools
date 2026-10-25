import { useEffect, useLayoutEffect, useRef } from "react"
import { fmt } from "@/lib/nutrition"
import { RING_MS, tween } from "@/lib/motion"

/**
 * A number that runs from its last value (or from `from` on first paint) to the new one on the ring curve.
 * The span's text is written here and never by React, so the running count and a re-render never meet.
 */
export function AnimatedNumber({ value, from, className }: { value: number; from?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const shown = useRef(from ?? value)

  useLayoutEffect(() => {
    if (ref.current && !ref.current.textContent) ref.current.textContent = fmt(shown.current)
  }, [])

  useEffect(() => {
    const start = shown.current
    return tween(RING_MS, (k) => {
      shown.current = start + (value - start) * k
      if (ref.current) ref.current.textContent = fmt(shown.current)
    })
  }, [value])

  return <span ref={ref} className={className} />
}
