import { RollingNumber } from "@/components/RollingNumber"
import { money, plural } from "@/lib/format"
import { isClosed, openTotal, stageSummary, weightedTotal, type Deal, type Stage } from "@/lib/pipeline"
import { cn } from "@/lib/utils"

/** The weighted value of the pipeline: each open deal's value times its stage's probability. */
export function Headline({ deals, stages, status, compact }: { deals: Deal[]; stages: Stage[]; status: string; compact?: boolean }) {
  const weighted = weightedTotal(deals, stages)
  const open = deals.filter((deal) => !isClosed(deal)).length
  return (
    <section aria-label="Weighted pipeline" className="flex min-w-0 flex-col">
      <h2 className="text-[13px] font-medium text-muted-foreground">Weighted pipeline</h2>
      <p
        data-weighted={weighted}
        className={cn(
          "mt-1 font-semibold leading-none tracking-[-0.035em] text-headline [font-variation-settings:'opsz'_32]",
          compact ? "text-[44px]" : "text-[clamp(3.25rem,4.6vw,5.25rem)]",
        )}
      >
        <RollingNumber value={weighted} format={money} />
      </p>
      <Shares deals={deals} stages={stages} total={weighted} className={compact ? "mt-3" : "mt-4"} />
      <p className={cn("text-pretty text-muted-foreground", compact ? "mt-2 text-sm" : "mt-2.5 text-[15px]")}>
        of <span className="font-medium text-foreground tabular-nums">{money(openTotal(deals))}</span> open across {plural(open, "deal")}
      </p>
      <p aria-live="polite" className={cn("text-pretty text-foreground/85", compact ? "mt-1 line-clamp-2 text-sm" : "mt-auto pt-3 text-[15px]")} data-status="">
        {status}
      </p>
    </section>
  )
}

/** The headline's makeup: each stage's share of the weighted total, in the stage's color. */
function Shares({ deals, stages, total, className }: { deals: Deal[]; stages: Stage[]; total: number; className?: string }) {
  return (
    <div aria-hidden="true" className={cn("flex h-2 w-full max-w-md gap-[3px]", className)}>
      {stages.map((stage) => {
        const share = total > 0 ? stageSummary(deals, stage).weighted / total : 0
        return (
          <span
            key={stage.id}
            data-stage=""
            style={{ "--stage-raw": stage.color, flexGrow: share } as React.CSSProperties}
            className={cn("block min-w-0 basis-0 rounded-full bg-stage transition-[flex-grow] duration-700 ease-out-strong motion-reduce:transition-none", share === 0 && "hidden")}
          />
        )
      })}
    </div>
  )
}
