import { useSyncExternalStore } from "react"

export function useMedia(query: string): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const m = window.matchMedia(query)
      m.addEventListener("change", onChange)
      return () => m.removeEventListener("change", onChange)
    },
    () => window.matchMedia(query).matches,
  )
}

export const useDesktop = () => useMedia("(min-width: 1024px)")
export const useReducedMotion = () => useMedia("(prefers-reduced-motion: reduce)")
