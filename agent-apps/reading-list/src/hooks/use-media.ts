import { useSyncExternalStore } from "react"

/** Whether a media query matches now, kept current as the window changes. */
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

/** The front page's column count: four on a desktop, two on a tablet, one on a phone. */
export function useColumns(): number {
  const four = useMedia("(min-width: 1100px)")
  const two = useMedia("(min-width: 680px)")
  return four ? 4 : two ? 2 : 1
}
