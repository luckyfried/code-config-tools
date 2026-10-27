import { useSyncExternalStore } from "react"

const query = "(prefers-reduced-motion: reduce)"

export function useReducedMotion() {
  return useSyncExternalStore(
    (listener) => {
      const media = window.matchMedia(query)
      media.addEventListener("change", listener)
      return () => media.removeEventListener("change", listener)
    },
    () => window.matchMedia(query).matches,
    () => false,
  )
}
