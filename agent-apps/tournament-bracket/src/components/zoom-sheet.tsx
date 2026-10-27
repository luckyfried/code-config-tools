import { useRef, useState, type ReactNode } from "react"
import { MinusIcon, PlusIcon } from "lucide-react"
import { Button } from "@/components/ui/button"

/** A pan-and-zoom frame: two fingers pinch, one finger pans the scroll, and the buttons step the zoom. */
export function ZoomSheet({ base, children }: { base: number; children: (width: number) => ReactNode }) {
  const [scale, setScale] = useState(1)
  const frame = useRef<HTMLDivElement>(null)
  const touches = useRef(new Map<number, { x: number; y: number }>())
  const pinch = useRef<{ dist: number; scale: number } | null>(null)

  const clamp = (s: number) => Math.min(4, Math.max(1, s))
  const zoomTo = (next: number) => {
    const el = frame.current
    const s = clamp(next)
    if (el) {
      // Keep the middle of the view where it is.
      const cx = (el.scrollLeft + el.clientWidth / 2) / scale
      const cy = (el.scrollTop + el.clientHeight / 2) / scale
      requestAnimationFrame(() => {
        el.scrollLeft = cx * s - el.clientWidth / 2
        el.scrollTop = cy * s - el.clientHeight / 2
      })
    }
    setScale(s)
  }

  const spread = () => {
    const [a, b] = [...touches.current.values()]
    return Math.hypot(a.x - b.x, a.y - b.y)
  }

  return (
    <div className="flex min-h-0 flex-col gap-2">
      <div
        ref={frame}
        className="max-h-[70dvh] touch-pan-x touch-pan-y overflow-auto overscroll-contain"
        onPointerDown={(e) => {
          if (e.pointerType !== "touch") return
          touches.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
          if (touches.current.size === 2) pinch.current = { dist: spread(), scale }
        }}
        onPointerMove={(e) => {
          if (!touches.current.has(e.pointerId)) return
          touches.current.set(e.pointerId, { x: e.clientX, y: e.clientY })
          if (pinch.current && touches.current.size === 2) zoomTo((pinch.current.scale * spread()) / pinch.current.dist)
        }}
        onPointerUp={(e) => {
          touches.current.delete(e.pointerId)
          if (touches.current.size < 2) pinch.current = null
        }}
        onPointerCancel={(e) => {
          touches.current.delete(e.pointerId)
          pinch.current = null
        }}
      >
        {children(base * scale)}
      </div>
      <div className="flex justify-end gap-1.5">
        <Button size="icon" variant="secondary" aria-label="Zoom out" onClick={() => zoomTo(scale / 1.5)} disabled={scale <= 1}>
          <MinusIcon />
        </Button>
        <Button size="icon" variant="secondary" aria-label="Zoom in" onClick={() => zoomTo(scale * 1.5)} disabled={scale >= 4}>
          <PlusIcon />
        </Button>
      </div>
    </div>
  )
}
