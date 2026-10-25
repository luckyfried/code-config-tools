import { useCallback } from "react"

/**
 * Sets --i, the tile's place in the wall that staggers its reveal, and --vt, the name that carries the tile from the
 * wall to TV mode and back, without a style attribute.
 */
export function useStagger(index: number) {
  return useCallback(
    (element: HTMLElement | null) => {
      element?.style.setProperty("--i", String(index))
      element?.style.setProperty("--vt", `tile-${index}`)
    },
    [index],
  )
}
