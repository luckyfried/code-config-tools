import { useId } from "react"
import { cn } from "cn"
import { clientColor, config } from "@/lib/config"
import { useSize } from "@/lib/hooks"
import type { Entry } from "@/lib/store"
import { HOUR, format, isSameDay, msOnDay } from "@/lib/time"

type Props = {
  days: Date[]
  entries: Entry[]
  now: number
  height?: number
  /** Grow to the room the panel gives it, never shorter than height. */
  fill?: boolean
  onSelectDay: (day: Date) => void
}

// The week as stacked bars, one segment per client in the inputs' order; data-total is the week's hours.
export function WeekBars({ days, entries, now, height: minHeight = 260, fill = false, onSelectDay }: Props) {
  const [ref, size] = useSize<HTMLDivElement>()
  const width = size.width
  const height = fill ? Math.min(Math.max(size.height, minHeight), 820) : minHeight
  const sheen = `sheen-${useId().replace(/:/g, "")}`
  const perDay = days.map((day) =>
    config.clients.map((c) => entries.reduce((sum, e) => (e.clientId === c.id ? sum + msOnDay(e, day, now) : sum), 0)),
  )
  const dayTotals = perDay.map((parts) => parts.reduce((a, b) => a + b, 0))
  const total = dayTotals.reduce((a, b) => a + b, 0)
  const peak = Math.max(...dayTotals) / HOUR
  const top = Math.max(8, Math.ceil(peak / 2) * 2)

  const gutter = 30
  const labelH = 34
  const headH = 22
  const plotH = height - labelH - headH
  const slot = width > gutter ? (width - gutter) / 7 : 0
  const barW = Math.min(slot * 0.58, 64)
  const y = (h: number) => headH + plotH - (h / top) * plotH
  const ticks = Array.from({ length: top / 2 + 1 }, (_, i) => i * 2)
  const today = new Date(now)

  return (
    <div
      ref={ref}
      className={cn("w-full", fill && "relative min-h-(--h) flex-1")}
      style={{ "--h": `${minHeight}px` } as React.CSSProperties}
    >
      {width > 0 ? (
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          data-total={(total / HOUR).toFixed(2)}
          role="img"
          aria-label={`${(total / HOUR).toFixed(1)} hours this week`}
          className={cn("block overflow-visible", fill && "absolute inset-x-0 bottom-0")}
        >
          <defs>
            <linearGradient id={sheen} x1="0" x2="1" y1="0" y2="0">
              <stop offset="0" stopColor="white" stopOpacity="0.26" />
              <stop offset="0.38" stopColor="white" stopOpacity="0.06" />
              <stop offset="0.62" stopColor="black" stopOpacity="0" />
              <stop offset="1" stopColor="black" stopOpacity="0.16" />
            </linearGradient>
          </defs>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={gutter} x2={width} y1={y(t)} y2={y(t)} className={cn("stroke-rule", t === 0 && "stroke-border")} />
              <text x={gutter - 8} y={y(t) + 4} textAnchor="end" className="fill-muted-foreground font-mono text-[11px]">
                {t}
              </text>
            </g>
          ))}
          {days.map((day, i) => {
            const cx = gutter + slot * i + slot / 2
            const isToday = isSameDay(day, today)
            let acc = 0
            let stack = 0
            const hoursLabel = (dayTotals[i] / HOUR).toFixed(1)
            return (
              <g
                key={day.toISOString()}
                role="button"
                tabIndex={0}
                data-hours={(dayTotals[i] / HOUR).toFixed(2)}
                aria-label={`${format(day, "EEEE")}, ${hoursLabel} hours`}
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
                  x={cx - slot / 2 + 2}
                  y={headH - 4}
                  width={slot - 4}
                  height={plotH + labelH}
                  rx={6}
                  className="fill-transparent transition-[fill] duration-150 group-hover:fill-accent/50 group-focus-visible:fill-accent"
                />
                {perDay[i].map((ms, ci) => {
                  if (ms <= 0) return null
                  const h0 = acc
                  acc += ms / HOUR
                  const yTop = y(acc)
                  const segH = Math.max(1, y(h0) - yTop - (h0 > 0 ? 2 : 0))
                  const order = stack++
                  return (
                    <g key={config.clients[ci].id} className="rise" style={{ "--d": i, "--s": order, "--c": clientColor(config.clients[ci].id) } as React.CSSProperties}>
                      <rect x={cx - barW / 2} y={yTop} width={barW} height={segH} rx={Math.min(4, barW / 6)} className="fill-(--c)" />
                      <rect x={cx - barW / 2} y={yTop} width={barW} height={segH} rx={Math.min(4, barW / 6)} fill={`url(#${sheen})`} />
                    </g>
                  )
                })}
                {dayTotals[i] > 0 ? (
                  <text
                    x={cx}
                    y={y(dayTotals[i] / HOUR) - 8}
                    textAnchor="middle"
                    className="land fill-foreground font-mono text-[12px] font-medium"
                    style={{ "--d": i, "--s": Math.max(0, stack - 1) } as React.CSSProperties}
                  >
                    {hoursLabel}
                  </text>
                ) : null}
                <text
                  x={cx}
                  y={height - 14}
                  textAnchor="middle"
                  className={cn("text-[12px]", isToday ? "fill-foreground font-semibold" : "fill-muted-foreground")}
                >
                  {format(day, slot < 46 ? "EEEEE" : "EEE d")}
                </text>
                {isToday ? <circle cx={cx} cy={height - 3} r={2.5} className="fill-foreground" /> : null}
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
