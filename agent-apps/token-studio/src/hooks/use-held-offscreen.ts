import { useEffect, useRef, useState } from "react"
import { catchUp } from "./use-live-tokens"

/** How long a value has to stay put before the views scrolled away take it anyway. */
const SETTLE_MS = 300

/**
 * A value that follows while its region is on screen, or within a short scroll of it, and holds still while the
 * region is scrolled away and the value is moving, so the memoized views inside skip their renders and the live
 * parts inside skip their restyles. The region catches up as it comes back toward view, or once the value settles.
 * `value` must keep its identity while it does not change.
 */
export function useHeldOffscreen<T>(value: T) {
  const ref = useRef<HTMLDivElement>(null)
  const [near, setNear] = useState(true)
  const [settled, setSettled] = useState(value)
  const [shown, setShown] = useState(value)
  const follow = near || settled === value
  if (follow && shown !== value) setShown(value)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const watch = new IntersectionObserver(
      ([entry]) => {
        el.toggleAttribute("data-away", !entry.isIntersecting)
        if (entry.isIntersecting) catchUp(el)
        setNear(entry.isIntersecting)
      },
      { rootMargin: "120px 0px", scrollMargin: "120px 0px" },
    )
    watch.observe(el)
    return () => watch.disconnect()
  }, [])

  useEffect(() => {
    if (near || settled === value) return
    const timer = setTimeout(() => {
      if (ref.current) catchUp(ref.current)
      setSettled(value)
    }, SETTLE_MS)
    return () => clearTimeout(timer)
  }, [near, settled, value])

  return [ref, follow ? value : shown] as const
}
