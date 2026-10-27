import { cn } from "cn"
import { useWidth } from "@/lib/hooks"
import type { Entry } from "@/lib/store"
import { HOUR, format, isSameDay, msOnDay } from "@/lib/time"

type Props = {
  days: Date[]
  entries: Entry[]
  now: number
  height?: number
  showHours?: boolean
  onSelectDay: (day: Date) => void
}

// Six steps of tint: none, then up to eight hours and over.
export function heatLevel(hours: number): number {
  if (hours <= 0) return 0
  return Math.min(5, Math.ceil(hours / 1.6))
}

// The month as one strip of days, each filled from its foot with a tint for its hours.
export function MonthStrip({ days, entries, now, height = 44, showHours = false, onSelectDay }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const gap = width < 500 ? 2 : 4
  const n = days.length
  const cellW = width > 0 ? (width - gap * (n - 1)) / n : 0
  const labelH = 22
  const today = new Date(now)
  const sparse = cellW < 20

  return (
    <div ref={ref} className="w-full" style={{ "--h": `${height + labelH}px` } as React.CSSProperties}>
      {width > 0 ? (
        <svg width={width} height={height + labelH} viewBox={`0 0 ${width} ${height + labelH}`} role="img" aria-label="Hours by day this month" className="block overflow-visible">
          {days.map((day, i) => {
            const ms = entries.reduce((sum, e) => sum + msOnDay(e, day, now), 0)
            const h = ms / HOUR
            const level = heatLevel(h)
            const x = i * (cellW + gap)
            const future = day.getTime() > now && !isSameDay(day, today)
            const isToday = isSameDay(day, today)
            const d = day.getDate()
            const label = !sparse || d === 1 || d % 7 === 1 || isToday
            return (
              <g
                key={d}
                role="button"
                tabIndex={0}
                data-hours={h.toFixed(2)}
                aria-label={`${format(day, "MMMM d")}, ${h.toFixed(1)} hours`}
                onClick={() => onSelectDay(day)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault()
                    onSelectDay(day)
                  }
                }}
                className="group cursor-pointer outline-none"
              >
                <rect
                  x={x}
                  y={0}
                  width={cellW}
                  height={height}
                  rx={Math.min(5, cellW / 4)}
                  className={cn("heat-0", future && "opacity-40", "group-hover:opacity-80")}
                />
                {level > 0 ? (
                  <rect
                    x={x}
                    y={0}
                    width={cellW}
                    height={height}
                    rx={Math.min(5, cellW / 4)}
                    className={cn(`heat-${level}`, "fill-up group-hover:opacity-80")}
                    style={{ "--i": i } as React.CSSProperties}
                  />
                ) : null}
                <rect
                  x={x - 0.75}
                  y={-0.75}
                  width={cellW + 1.5}
                  height={height + 1.5}
                  rx={Math.min(5, cellW / 4) + 0.75}
                  className={cn(
                    "fill-none stroke-transparent group-focus-visible:stroke-ring group-focus-visible:stroke-2",
                    isToday && "ring-in stroke-foreground stroke-[1.5]",
                  )}
                  style={{ "--i": i } as React.CSSProperties}
                />
                {showHours && h > 0 && cellW >= 30 ? (
                  <text
                    x={x + cellW / 2}
                    y={height / 2 + 4}
                    textAnchor="middle"
                    className={cn("fill-up pointer-events-none font-mono text-[11px] font-medium", level >= 3 ? "fill-background" : "fill-foreground")}
                    style={{ "--i": i } as React.CSSProperties}
                  >
                    {h.toFixed(1)}
                  </text>
                ) : null}
                {label ? (
                  <text
                    x={x + cellW / 2}
                    y={height + 16}
                    textAnchor="middle"
                    className={cn("font-mono text-[11px]", isToday ? "fill-foreground font-semibold" : "fill-muted-foreground")}
                  >
                    {d}
                  </text>
                ) : null}
              </g>
            )
          })}
        </svg>
      ) : (
        <div className="h-(--h)" />
      )}
    </div>
  )
}

export function HeatLegend() {
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground" aria-hidden>
      <span>0 h</span>
      {[0, 1, 2, 3, 4, 5].map((l) => (
        <svg key={l} width="14" height="14" viewBox="0 0 14 14">
          <rect width="14" height="14" rx="3" className={`heat-${l}`} />
        </svg>
      ))}
      <span>8 h</span>
    </div>
  )
}
