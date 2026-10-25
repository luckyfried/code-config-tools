import { useCallback, useMemo, useRef } from "react"
import { CheckIcon } from "lucide-react"
import { cn } from "cn"

import { Card } from "@/components/ui/card"
import { DeltaChip } from "@/components/delta-chip"
import { Sparkline } from "@/components/sparkline"
import type { Copy, Metric } from "@/lib/config"
import { decimalsOf, formatDay, formatValue } from "@/lib/format"
import { deltaOf, goalMet, latest } from "@/lib/metrics"
import { useCountUp } from "@/hooks/use-count-up"
import { useStagger } from "@/hooks/use-stagger"

const SIZE_CLASS: Record<Metric["size"], string> = {
  "1x1": "",
  "2x1": "sm:col-span-2",
  "2x2": "row-span-2 sm:col-span-2",
}

export function Tile({
  metric,
  index,
  group,
  entrance,
  reveal,
  copy,
  onOpen,
}: {
  metric: Metric
  index: number
  /** The tile's group on the wall, which picks its hue. */
  group: number
  /** The tile rises in when the page first opens. */
  entrance: boolean
  /** The figure counts up and the sparkline draws, once, on the view the page opens on. */
  reveal: boolean
  copy: Copy
  onOpen: (id: string) => void
}) {
  const point = latest(metric)
  const delta = deltaOf(metric)
  const met = goalMet(metric)
  const big = metric.size === "2x2"
  const wide = metric.size !== "1x1"
  const side = metric.size === "2x1"
  const decimals = useMemo(() => decimalsOf(metric.history), [metric.history])
  const format = useCallback((value: number) => formatValue(metric, value, decimals), [metric, decimals])
  const figure = useRef<HTMLSpanElement>(null)
  const stagger = useStagger(index)
  useCountUp(figure, point?.value ?? 0, format, index, reveal)

  const goalText = metric.goal != null ? `${copy.goal} ${format(metric.goal)}` : null

  return (
    <div
      ref={stagger}
      data-metric={metric.id}
      data-size={metric.size}
      data-delta={delta ? String(delta.change) : undefined}
      data-goal-met={met ? "true" : undefined}
      data-group={group % 4}
      className={cn("tile-move relative min-w-0", entrance && "tile-enter", reveal && "reveal", SIZE_CLASS[metric.size])}
    >
      <Card
        className={cn(
          "tile-surface relative h-full gap-0 py-0 ring-0 transition-[translate] duration-200 ease-out",
          side && "sm:flex-row",
          "has-[button:focus-visible]:outline-2 has-[button:focus-visible]:outline-ring",
          "pointer-fine:hover:-translate-y-0.5",
          "in-data-[tv=on]:[container-type:size]",
        )}
      >
        <div className={cn("flex min-w-0 flex-col", side && "sm:max-w-[58%] sm:shrink-0 sm:pb-5")}>
          <div className="flex items-start justify-between gap-3 px-6 pt-5">
            <h3 className="min-w-0">
              <button
                type="button"
                onClick={() => onOpen(metric.id)}
                className="block max-w-full truncate text-left text-label font-medium text-muted-foreground outline-none after:absolute after:inset-0 after:z-10 after:rounded-[inherit] after:content-[''] in-data-[tv=on]:text-[min(1.25rem,5.5cqi)]"
              >
                {metric.label}
              </button>
            </h3>
            {delta && (
              <DeltaChip delta={delta} className="in-data-[tv=on]:h-8 in-data-[tv=on]:px-3 in-data-[tv=on]:text-label" />
            )}
          </div>

          <div className="flex items-baseline gap-2 px-6 pt-2">
            <span
              ref={figure}
              className={cn(
                "figure font-semibold text-card-foreground",
                big ? "text-[4.5rem] sm:text-hero" : "text-figure",
                big
                  ? "in-data-[tv=on]:text-[clamp(6rem,min(30cqh,16cqi),18rem)]"
                  : side
                    ? "in-data-[tv=on]:text-[clamp(3rem,min(34cqh,9cqi),10rem)]"
                    : "in-data-[tv=on]:text-[clamp(3rem,min(34cqh,18cqi),10rem)]",
              )}
            >
              {point ? format(point.value) : copy.noReadings}
            </span>
            {metric.format === "number" && metric.unit && (
              <span className="truncate text-label text-muted-foreground in-data-[tv=on]:text-title">{metric.unit}</span>
            )}
          </div>

          {wide && (delta || goalText) && (
            <p
              className={cn(
                "flex-wrap items-center gap-x-3 gap-y-1 px-6 pt-3 text-xs text-muted-foreground in-data-[tv=on]:text-label",
                big ? "flex" : "mt-auto hidden sm:flex",
              )}
            >
              {delta && (
                <span>
                  {copy.since} {formatDay(delta.since)}
                </span>
              )}
              {goalText && (
                <span className={cn("inline-flex items-center gap-1", met && "text-positive")}>
                  {met && <CheckIcon className="size-3.5" aria-hidden="true" />}
                  {goalText}
                </span>
              )}
            </p>
          )}
          {!wide && met && <span className="sr-only">{copy.goalMet}</span>}
          {!delta && point && (
            <p className="px-6 pt-3 text-xs text-muted-foreground">
              {copy.firstReading} {formatDay(point.date)}
            </p>
          )}
        </div>

        <Sparkline
          metric={metric}
          delta={delta}
          reveal={reveal}
          className={cn("mt-auto flex-1 pt-2", side && "sm:mt-0 sm:min-w-0 sm:self-stretch sm:pt-5 sm:pb-1 sm:pl-2")}
        />
      </Card>
      {met && <span className="goal-glow rounded-xl" aria-hidden="true" />}
    </div>
  )
}
