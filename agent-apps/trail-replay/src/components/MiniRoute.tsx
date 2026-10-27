import { useId } from "react"
import { cn } from "@/lib/utils"

interface MiniRouteProps {
  points: [number, number][]
  className?: string
  label: string
}

/** The route's shape, drawn as one line with the ramp's colors from start to finish. */
export function MiniRoute({ points, className, label }: MiniRouteProps) {
  const id = useId()
  const xs = points.map((p) => p[0])
  const ys = points.map((p) => p[1])
  const w = Math.max(...xs) - Math.min(...xs) || 1
  const h = Math.max(...ys) - Math.min(...ys) || 1
  const size = Math.max(w, h)
  const ox = Math.min(...xs) - (size - w) / 2
  const oy = Math.min(...ys) - (size - h) / 2
  const d = points
    .map(([x, y], i) => `${i ? "L" : "M"}${(((x - ox) / size) * 100).toFixed(1)} ${(((y - oy) / size) * 100).toFixed(1)}`)
    .join("")
  const [sx, sy] = points[0]
  return (
    <svg viewBox="-8 -8 116 116" className={cn("overflow-visible", className)} role="img" aria-label={label}>
      <defs>
        <linearGradient id={id} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="var(--ramp-1)" />
          <stop offset="0.35" stopColor="var(--ramp-2)" />
          <stop offset="0.6" stopColor="var(--ramp-3)" />
          <stop offset="0.85" stopColor="var(--ramp-4)" />
          <stop offset="1" stopColor="var(--ramp-5)" />
        </linearGradient>
      </defs>
      <path d={d} fill="none" stroke="var(--track-casing)" strokeOpacity="0.1" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      <path d={d} fill="none" stroke={`url(#${id})`} strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={((sx - ox) / size) * 100} cy={((sy - oy) / size) * 100} r="3.5" className="fill-background stroke-foreground" strokeWidth="2" />
    </svg>
  )
}
