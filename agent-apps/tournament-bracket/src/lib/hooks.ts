import { useEffect, useLayoutEffect, useRef, useState } from "react"

export function useMedia(query: string): boolean {
  const [on, setOn] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const change = () => setOn(mq.matches)
    change()
    mq.addEventListener("change", change)
    return () => mq.removeEventListener("change", change)
  }, [query])
  return on
}

export const useReducedMotion = () => useMedia("(prefers-reduced-motion: reduce)")

/** The width of an element, kept current as it resizes. */
export function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    setWidth(el.clientWidth)
    const ro = new ResizeObserver(() => setWidth(el.clientWidth))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, width]
}

/** The theme names its own scheme in --scheme; shadcn's dark styles follow it through data-scheme on the root. */
export function useScheme() {
  useEffect(() => {
    const root = document.documentElement
    const apply = () => {
      const scheme = getComputedStyle(root).getPropertyValue("--scheme").trim() || "light"
      root.dataset.scheme = scheme
    }
    apply()
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    mq.addEventListener("change", apply)
    return () => mq.removeEventListener("change", apply)
  }, [])
}
