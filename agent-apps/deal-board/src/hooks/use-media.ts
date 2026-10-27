import { useSyncExternalStore } from "react"

/** Whether a media query matches now, following it as it changes. */
export function useMedia(query: string): boolean {
  return useSyncExternalStore(
    (change) => {
      const list = window.matchMedia(query)
      list.addEventListener("change", change)
      return () => list.removeEventListener("change", change)
    },
    () => window.matchMedia(query).matches,
  )
}

export const WIDE = "(min-width: 1024px)"

/** A phone on its side, or any screen too short for the headline, funnel, and a column at once. */
export const SHORT = "(max-height: 560px)"
