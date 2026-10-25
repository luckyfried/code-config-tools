import { Area, AreaChart, ReferenceLine, YAxis } from "recharts"
import { cn } from "cn"

import { ChartContainer, type ChartConfig } from "@/components/ui/chart"
import type { Metric } from "@/lib/config"
import { domainOf, sparkPoints, type Delta } from "@/lib/metrics"

const config = { value: { label: "Reading", color: "var(--spark)" } } satisfies ChartConfig

type DotProps = { cx?: number; cy?: number; index?: number }

const TONE = { good: "var(--positive)", bad: "var(--negative)", flat: "var(--color-value)" }

/**
 * The last thirty readings as a line in the group's hue over a three-stop gradient fill, with a soft glow under the
 * line; it draws left to right once when the tile is revealed. The goal is a hairline. The end dot takes the color of
 * the latest change, good or bad, and sits inside the tile with room for its halo.
 */
export function Sparkline({
  metric,
  delta,
  reveal,
  className,
}: {
  metric: Metric
  delta: Delta | null
  reveal: boolean
  className?: string
}) {
  const points = sparkPoints(metric)
  if (points.length < 2) return null
  const domain = domainOf(points.map((p) => p.value), metric.goal)
  const last = points.length - 1
  const gradientId = `spark-fill-${metric.id}`
  const tone = delta?.good == null ? TONE.flat : delta.good ? TONE.good : TONE.bad

  const renderDot = ({ cx, cy, index: i }: DotProps) =>
    i === last && cx != null && cy != null ? (
      <g key="last">
        <circle cx={cx} cy={cy} r={8} fill={tone} opacity={0.18} />
        <circle cx={cx} cy={cy} r={4} fill={tone} stroke="var(--card)" strokeWidth={1.5} />
      </g>
    ) : (
      <g key={`dot-${i}`} />
    )

  return (
    <div className={cn("sparkline min-h-12 w-full", reveal && "spark-reveal", className)} aria-hidden="true">
      <ChartContainer config={config} className="aspect-auto size-full" initialDimension={{ width: 320, height: 64 }}>
        <AreaChart data={points} margin={{ top: 14, right: 18, bottom: 12, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" className="spark-fill-top" />
              <stop offset="55%" className="spark-fill-mid" />
              <stop offset="100%" className="spark-fill-end" />
            </linearGradient>
          </defs>
          <YAxis hide domain={domain} />
          {metric.goal != null && (
            <ReferenceLine y={metric.goal} stroke="var(--goal)" strokeWidth={1} strokeDasharray="3 3" ifOverflow="extendDomain" />
          )}
          <Area
            className="spark-glow"
            dataKey="value"
            type="monotone"
            stroke="var(--color-value)"
            strokeWidth={7}
            fill="none"
            dot={false}
            activeDot={false}
            isAnimationActive={false}
            baseValue={domain[0]}
          />
          <Area
            dataKey="value"
            type="monotone"
            stroke="var(--color-value)"
            strokeWidth={2.25}
            fill={`url(#${gradientId})`}
            dot={renderDot}
            activeDot={false}
            isAnimationActive={false}
            baseValue={domain[0]}
          />
        </AreaChart>
      </ChartContainer>
    </div>
  )
}
