import { useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react"
import { XIcon } from "lucide-react"
import { Button } from "@/components/ui/button"

type Props = { title: string; leave: string; ratio: number; onClose: () => void; children: (width: number) => ReactNode; foot: ReactNode }

/** The TV view: the bracket at the full width of the screen; one taller than the screen pans slowly down and back. */
export function BigScreen({ title, leave, ratio, onClose, children, foot }: Props) {
  const stage = useRef<HTMLDivElement>(null)
  const [box, setBox] = useState({ w: window.innerWidth, h: window.innerHeight })

  useLayoutEffect(() => {
    const el = stage.current
    if (!el) return
    const measure = () => setBox({ w: el.clientWidth, h: el.clientHeight })
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const key = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    window.addEventListener("keydown", key)
    return () => window.removeEventListener("keydown", key)
  }, [onClose])

  const width = Math.max(0, box.w - 48)
  const height = width * ratio
  const over = height - box.h
  const pan = over > 8 ? ({ "--pan-by": `${-over - 24}px`, "--pan-ms": `${Math.round(8000 + over * 40)}ms` } as CSSProperties) : undefined

  return (
    <div className="fixed inset-0 z-40 flex flex-col bg-background bg-(image:--backdrop)" role="dialog" aria-modal="true" aria-label={title}>
      <header className="flex items-center justify-between gap-4 px-6 pt-5 pb-3">
        <h1 className="display truncate text-5xl uppercase">{title}</h1>
        <Button variant="outline" onClick={onClose}>
          <XIcon />
          {leave}
        </Button>
      </header>
      <div ref={stage} className={`min-h-0 flex-1 overflow-hidden px-6 ${pan ? "" : "flex items-center"}`}>
        <div className={pan ? "pan" : ""} style={pan}>
          {children(width)}
        </div>
      </div>
      <footer className="px-6 pt-2 pb-5">{foot}</footer>
    </div>
  )
}
