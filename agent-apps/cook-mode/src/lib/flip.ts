import { useLayoutEffect, useRef } from "react"

/**
 * FLIP for a wrapping row: children marked with data-flip="<key>" glide from
 * where they were to where they now sit whenever `version` changes.
 */
export function useFlip<T extends HTMLElement>(version: unknown) {
  const ref = useRef<T>(null)
  const last = useRef(new Map<string, DOMRect>())

  useLayoutEffect(() => {
    const root = ref.current
    if (!root) return
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const next = new Map<string, DOMRect>()
    root.querySelectorAll<HTMLElement>("[data-flip]").forEach((element) => {
      const key = element.dataset.flip!
      const rect = element.getBoundingClientRect()
      next.set(key, rect)
      const before = last.current.get(key)
      if (reduce) return
      if (before) {
        const dx = before.left - rect.left
        const dy = before.top - rect.top
        if (Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5) {
          element.animate(
            [{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "translate(0, 0)" }],
            { duration: 260, easing: "cubic-bezier(0.23, 1, 0.32, 1)" },
          )
        }
      } else if (last.current.size > 0) {
        element.animate(
          [{ opacity: 0, transform: "scale(0.94)" }, { opacity: 1, transform: "scale(1)" }],
          { duration: 220, easing: "cubic-bezier(0.23, 1, 0.32, 1)" },
        )
      }
    })
    last.current = next
  }, [version])

  return ref
}
