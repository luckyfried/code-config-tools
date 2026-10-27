import { useLayoutEffect, useRef, useState, type ReactNode } from "react"
import { cn } from "@/lib/utils"

interface StepPagerProps {
  step: number
  render: (step: number) => ReactNode
  onSwipe?: (direction: "next" | "prev") => void
  className?: string
  pageClassName?: string
}

interface Page {
  step: number
  motion: string
}

const SWIPE_PX = 56

/**
 * One step per page. A new step slides in from the side it comes from while
 * the old one slides out (240 ms, ease-out); a horizontal drag turns the page.
 */
export function StepPager({ step, render, onSwipe, className, pageClassName }: StepPagerProps) {
  const [pages, setPages] = useState<Page[]>([{ step, motion: "" }])
  const shown = useRef(step)
  const box = useRef<HTMLDivElement>(null)
  const drag = useRef<{ x: number; y: number; id: number; moved: boolean; t: number } | null>(null)
  const swallowClick = useRef(false)

  useLayoutEffect(() => {
    if (step === shown.current) return
    const direction = step > shown.current ? "next" : "prev"
    setPages([
      { step: shown.current, motion: `page-out-${direction}` },
      { step, motion: `page-in-${direction}` },
    ])
    shown.current = step
    const done = window.setTimeout(() => setPages([{ step, motion: "" }]), 260)
    return () => window.clearTimeout(done)
  }, [step])

  const current = () => box.current?.querySelector<HTMLElement>("[data-page-current]") ?? null

  return (
    <div
      ref={box}
      className={cn("relative grid touch-pan-y overflow-x-clip", className)}
      onPointerDown={(event) => {
        if (!onSwipe || event.button !== 0) return
        drag.current = { x: event.clientX, y: event.clientY, id: event.pointerId, moved: false, t: performance.now() }
      }}
      onPointerMove={(event) => {
        const start = drag.current
        if (!start || start.id !== event.pointerId) return
        const dx = event.clientX - start.x
        const dy = event.clientY - start.y
        if (!start.moved && Math.abs(dx) > 8 && Math.abs(dx) > Math.abs(dy)) {
          start.moved = true
          event.currentTarget.setPointerCapture(event.pointerId)
        }
        if (start.moved) {
          const page = current()
          if (page) page.style.transform = `translateX(${dx * 0.55}px)`
        }
      }}
      onPointerUp={(event) => {
        const start = drag.current
        drag.current = null
        if (!start || !start.moved || start.id !== event.pointerId) return
        swallowClick.current = true
        const dx = event.clientX - start.x
        const speed = Math.abs(dx) / Math.max(1, performance.now() - start.t)
        const page = current()
        if (page) page.style.transform = ""
        if (Math.abs(dx) > SWIPE_PX || speed > 0.5) onSwipe?.(dx < 0 ? "next" : "prev")
        else
          page?.animate([{ transform: `translateX(${dx * 0.55}px)` }, { transform: "translateX(0)" }], {
            duration: 200,
            easing: "cubic-bezier(0.23, 1, 0.32, 1)",
          })
      }}
      onPointerCancel={() => {
        drag.current = null
        const page = current()
        if (page) page.style.transform = ""
      }}
      onClickCapture={(event) => {
        if (swallowClick.current) {
          event.stopPropagation()
          event.preventDefault()
          swallowClick.current = false
        }
      }}
    >
      {pages.map((page, index) => {
        const leaving = pages.length > 1 && index === 0
        return (
          <div
            key={`${page.step}-${leaving ? "out" : "in"}`}
            className={cn("[grid-area:1/1]", page.motion, leaving && "pointer-events-none", pageClassName)}
            aria-hidden={leaving || undefined}
            data-page-current={leaving ? undefined : ""}
          >
            {render(page.step)}
          </div>
        )
      })}
    </div>
  )
}
