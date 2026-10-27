import { money, shortMoney } from "@/lib/format"
import type { Week } from "@/lib/pipeline"
import { cn } from "@/lib/utils"

/** Ninety days of closed deals by week: won value above the line, lost value below, the current week on the right. */
export function WonLostChart({ weeks, tall, className }: { weeks: Week[]; tall?: boolean; className?: string }) {
  const max = Math.max(1, ...weeks.flatMap((week) => [week.won, week.lost]))
  return (
    <div className={cn("flex flex-col", className)}>
      <div
        role="img"
        aria-label={`Won and lost by week over the last 90 days: ${weeks.filter((w) => w.wonCount > 0).length} weeks with wins, ${weeks.filter((w) => w.lostCount > 0).length} with losses.`}
        className={cn("grid flex-1 grid-rows-[1fr_auto_0.55fr]", tall ? "min-h-64" : "min-h-28")}
      >
        <div className="flex items-end gap-[3px]">
          {weeks.map((week) => (
            <span key={week.index} className="flex h-full flex-1 items-end" title={week.wonCount ? `${week.wonCount} won, ${money(week.won)}` : undefined}>
              <span
                className="block w-full origin-bottom rounded-t-[3px] bg-won transition-transform duration-500 ease-out motion-reduce:transition-none"
                style={{ height: "100%", transform: `scaleY(${week.won / max})` }}
              />
            </span>
          ))}
        </div>
        <span className="my-[3px] h-px bg-border" />
        <div className="flex items-start gap-[3px]">
          {weeks.map((week) => (
            <span key={week.index} className="flex h-full flex-1 items-start" title={week.lostCount ? `${week.lostCount} lost, ${money(week.lost)}` : undefined}>
              <span
                className="block w-full origin-top rounded-b-[3px] bg-lost transition-transform duration-500 ease-out motion-reduce:transition-none"
                style={{ height: "100%", transform: `scaleY(${Math.min(1, (week.lost / max) * 1.8)})` }}
              />
            </span>
          ))}
        </div>
      </div>
      <div className="mt-1.5 flex justify-between text-xs text-muted-foreground">
        <span>13 weeks ago</span>
        <span>This week</span>
      </div>
    </div>
  )
}

export function Legend({ won, lost }: { won: number; lost: number }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px]">
      <span className="flex items-center gap-1.5">
        <span className="size-2.5 rounded-[3px] bg-won" />
        Won <span className="font-medium tabular-nums">{shortMoney(won)}</span>
      </span>
      <span className="flex items-center gap-1.5">
        <span className="size-2.5 rounded-[3px] bg-lost" />
        Lost <span className="font-medium tabular-nums">{shortMoney(lost)}</span>
      </span>
    </div>
  )
}
