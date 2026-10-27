import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { ArrowDown } from "lucide-react"

// A lane's scrolling list. When it holds more than fits, the list ends at its last whole card and a count of the cards
// further down sits in the space under it, clear of every card, and scrolls on to them.
export function LaneBody({ className, size, children }: { className: string; size: number; children: ReactNode }) {
  const box = useRef<HTMLDivElement | null>(null)
  const ref = useRef<HTMLDivElement | null>(null)
  const list = useRef<HTMLDivElement | null>(null)
  const [below, setBelow] = useState(0)
  const count = useCallback(() => {
    const outer = box.current
    const el = ref.current
    const inner = list.current
    if (!outer || !el || !inner) return
    const items = [...inner.children] as HTMLElement[]
    const room = outer.clientHeight
    const ends = items.map((c) => c.offsetTop + c.offsetHeight)
    // A list that fits keeps its padding under the last card; one that does not ends just under its last whole card,
    // short of the next card's shadow, with the marker's row (its height and margins) under it.
    const pad = parseFloat(getComputedStyle(el).paddingBottom)
    if ((ends.at(-1) ?? 0) + pad <= room) {
      el.style.removeProperty("--fit")
      setBelow(0)
      return
    }
    const edge = 3
    const fit = ends.filter((end) => end + edge <= room - 56).at(-1) ?? ends[0] ?? 0
    el.style.setProperty("--fit", `${fit + edge}px`)
    const seen = el.scrollTop + fit + 1
    setBelow(ends.filter((end) => end > seen).length)
  }, [])
  useEffect(() => {
    count()
    const settled = window.setTimeout(count, 900)
    const watch = new ResizeObserver(count)
    if (box.current) watch.observe(box.current)
    if (list.current) watch.observe(list.current)
    return () => {
      window.clearTimeout(settled)
      watch.disconnect()
    }
  }, [count, size])
  return (
    <div ref={box} className="flex min-h-0 flex-1 flex-col">
      <div ref={ref} onScroll={count} className={className}>
        <div ref={list} className="lane-list relative flex flex-col gap-3">
          {children}
        </div>
      </div>
      {below > 0 && (
        <button
          type="button"
          onClick={() => ref.current?.scrollBy({ top: ref.current.clientHeight * 0.8, behavior: "smooth" })}
          className="mx-auto my-2.5 flex h-9 shrink-0 items-center gap-1.5 rounded-full bg-card px-4 text-sm font-semibold text-foreground shadow-md ring-1 ring-border"
        >
          {below} more below
          <ArrowDown className="size-4" aria-hidden="true" />
        </button>
      )}
    </div>
  )
}
