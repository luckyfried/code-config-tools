import { useLayoutEffect, useRef, type RefObject } from "react"

/**
 * Rows that change place glide there: after each commit, every child with data-flip-key is compared with where it
 * sat before and slides from the old place to the new one (transform only).
 */
export function useFlip(list: RefObject<HTMLElement | null>, signature: string) {
  const tops = useRef(new Map<string, number>())
  useLayoutEffect(() => {
    const el = list.current
    if (!el) return
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches
    const next = new Map<string, number>()
    for (const child of el.querySelectorAll<HTMLElement>(":scope > [data-flip-key]")) {
      const key = child.dataset.flipKey!
      const top = child.offsetTop
      next.set(key, top)
      const before = tops.current.get(key)
      if (before === undefined || before === top || reduce) continue
      child.getAnimations().forEach((a) => a.cancel())
      child.animate([{ transform: `translateY(${before - top}px)` }, { transform: "translateY(0)" }], {
        duration: 340,
        easing: "cubic-bezier(0.23, 1, 0.32, 1)",
      })
    }
    tops.current = next
  }, [list, signature])
}
