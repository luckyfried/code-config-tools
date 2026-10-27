import { useEffect, useId, useMemo, useRef } from "react"
import type { ReplayClock } from "@/lib/clock"
import { distanceUnit, distanceValue } from "@/lib/format"
import { sampleAtTime, totalDistance } from "@/lib/track"
import type { Track, Units } from "@/lib/types"
import { cn } from "@/lib/utils"

interface RouteOverviewProps {
  track: Track
  clock: ReplayClock
  units: Units
  className?: string
}

/** The whole route seen from above, the stretch already covered drawn in full color and the marker on it. */
export function RouteOverview({ track, clock, units, className }: RouteOverviewProps) {
  const id = useId()
  const done = useRef<SVGGElement>(null)
  const dot = useRef<SVGGElement>(null)
  const covered = useRef<HTMLSpanElement>(null)

  const shape = useMemo(() => {
    const k = Math.cos((track.lat[0] * Math.PI) / 180)
    const xs = track.lon.map((lon) => lon * k)
    const ys = track.lat.map((lat) => -lat)
    const minX = Math.min(...xs)
    const minY = Math.min(...ys)
    const w = Math.max(...xs) - minX || 1e-9
    const h = Math.max(...ys) - minY || 1e-9
    const scale = 100 / Math.max(w, h)
    const place = (i: number): [number, number] => [(xs[i] - minX) * scale, (ys[i] - minY) * scale]
    const d = track.lat.map((_, i) => `${i ? "L" : "M"}${place(i)[0].toFixed(2)} ${place(i)[1].toFixed(2)}`).join("")
    const project = (lat: number, lon: number): [number, number] => [(lon * k - minX) * scale, (-lat - minY) * scale]
    return { d, w: w * scale, h: h * scale, start: place(0), project }
  }, [track])

  useEffect(() => {
    const total = totalDistance(track) || 1
    const unit = distanceUnit(units)
    let shown = ""
    const draw = (t: number) => {
      const here = sampleAtTime(track, t)
      const [x, y] = shape.project(here.lat, here.lon)
      done.current?.setAttribute("stroke-dasharray", `${(here.d / total).toFixed(4)} 2`)
      dot.current?.setAttribute("transform", `translate(${x.toFixed(2)} ${y.toFixed(2)})`)
      const text = `${distanceValue(here.d, units).toFixed(2)} of ${distanceValue(total, units).toFixed(2)} ${unit}`
      if (text !== shown && covered.current) covered.current.textContent = shown = text
    }
    draw(clock.t)
    return clock.subscribe(draw)
  }, [track, clock, units, shape])

  const pad = 8
  return (
    <section className={cn("flex min-h-0 flex-col gap-3", className)} aria-labelledby={`${id}-title`}>
      <div className="flex items-baseline gap-2">
        <h2 id={`${id}-title`} className="text-sm font-medium">
          Whole route
        </h2>
        <span ref={covered} className="ml-auto text-xs text-muted-foreground tabular-nums" />
      </div>
      <svg
        viewBox={`${-pad} ${-pad} ${shape.w + pad * 2} ${shape.h + pad * 2}`}
        className="min-h-0 w-full flex-1 overflow-visible"
        role="img"
        aria-label={`The whole of ${track.name} from above`}
      >
        <defs>
          <linearGradient id={`${id}-ramp`} x1="0" y1="1" x2="1" y2="0">
            <stop offset="0" stopColor="var(--ramp-1)" />
            <stop offset="0.35" stopColor="var(--ramp-2)" />
            <stop offset="0.6" stopColor="var(--ramp-3)" />
            <stop offset="0.85" stopColor="var(--ramp-4)" />
            <stop offset="1" stopColor="var(--ramp-5)" />
          </linearGradient>
        </defs>
        <path d={shape.d} fill="none" stroke={`url(#${id}-ramp)`} strokeOpacity="0.35" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        <g ref={done} fill="none" strokeLinecap="round" strokeLinejoin="round">
          <path d={shape.d} pathLength={1} stroke="var(--comet)" strokeOpacity="0.35" strokeWidth="9" vectorEffect="non-scaling-stroke" />
          <path d={shape.d} pathLength={1} stroke={`url(#${id}-ramp)`} strokeWidth="3.5" vectorEffect="non-scaling-stroke" />
        </g>
        <circle cx={shape.start[0]} cy={shape.start[1]} r="1.6" className="fill-background stroke-foreground" strokeWidth="2" vectorEffect="non-scaling-stroke" />
        <g ref={dot}>
          <circle r="5" className="fill-comet" opacity="0.35" />
          <circle r="2.4" fill="var(--marker)" stroke="var(--marker-ring)" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
        </g>
      </svg>
    </section>
  )
}
