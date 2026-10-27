import { useEffect, useState, type ReactNode } from "react"
import { cn } from "@/lib/utils"

const GOAL = 30
const R = 44
const C = 2 * Math.PI * R

/** The thirty-wears ring: fills toward thirty, and closes with an overshoot once it reaches it. */
export function WearRing({ wears, children, className }: { wears: number; children?: ReactNode; className?: string }) {
  const [shown, setShown] = useState(false)
  useEffect(() => {
    const f = requestAnimationFrame(() => requestAnimationFrame(() => setShown(true)))
    return () => cancelAnimationFrame(f)
  }, [])
  const full = wears >= GOAL
  const progress = shown ? Math.min(wears, GOAL) / GOAL : 0
  return (
    <div className={cn("wear-ring relative", className)} data-full={full} data-shown={shown}>
      <svg viewBox="0 0 100 100" className="absolute inset-0 size-full -rotate-90" aria-hidden="true">
        <circle cx="50" cy="50" r={R} fill="none" stroke="var(--wear-track)" strokeWidth="5" />
        <circle
          className="wear-arc"
          cx="50"
          cy="50"
          r={R}
          fill="none"
          stroke={full ? "var(--wear-done)" : "var(--wear-fill)"}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={C}
          strokeDashoffset={C * (1 - progress)}
        />
      </svg>
      <div className="absolute inset-[16%] grid place-items-center">{children}</div>
    </div>
  )
}
