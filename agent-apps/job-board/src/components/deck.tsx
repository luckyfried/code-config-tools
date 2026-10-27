import { useEffect, useRef, type ReactNode } from "react"
import { cardEl } from "@/lib/motion"
import type { Card } from "@/types"

// The new openings as a pile: the top card whole, the next two showing their edges under it. When the top card
// goes, the one under it rises into its place.
export function Deck({ cards, empty, render }: { cards: Card[]; empty: string; render: (card: Card, depth: number) => ReactNode }) {
  const pile = cards.slice(0, 3)
  const top = pile[0]?.record.id
  const ref = useRef<HTMLDivElement | null>(null)
  const held = useRef(false)

  // A person going through the pile with the keys keeps going: the card that rises takes the focus the last one had.
  useEffect(() => {
    if (top && held.current && document.activeElement === document.body) cardEl(top)?.focus({ preventScroll: true })
  }, [top])

  if (!top) return <p className="px-2 py-10 text-center text-muted-foreground">{empty}</p>
  const more = cards.length - 1
  return (
    <div
      ref={ref}
      className="flex flex-col gap-5"
      onFocusCapture={() => {
        held.current = true
      }}
      onBlurCapture={(e) => {
        if (e.relatedTarget && !ref.current?.contains(e.relatedTarget as Node)) held.current = false
      }}
    >
      <div className="deck" data-size={pile.length}>
        {pile.map((c, depth) => render(c, depth))}
      </div>
      <p className="text-center text-sm text-muted-foreground tabular-nums">
        {more === 0 ? "The last one in the pile." : `${more} more under this one`}
      </p>
    </div>
  )
}
