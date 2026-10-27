import type { CSSProperties } from "react"
import { cn } from "@/lib/utils"

const kg = (n: number) => (Math.round(n * 10) / 10).toFixed(1)

/** Where the bar starts to warm, as a share of the limit, and where it is fully amber. */
const WARM_FROM = 0.6
const WARM_AT = 0.9
const warmth = (share: number) => Math.min(1, Math.max(0, (share - WARM_FROM) / (WARM_AT - WARM_FROM)))

type WeightBarProps = { packed: number; planned: number; limit: number; compact?: boolean; className?: string }

export function WeightBar({ packed, planned, limit, compact = false, className }: WeightBarProps) {
  const share = packed / limit
  const plannedShare = planned / limit
  const over = packed > limit
  const plannedOver = planned > limit
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span className="font-medium">Bag weight</span>
        <span className={cn("tabular-nums text-muted-foreground", over && "font-medium text-destructive")}>
          <span className={cn("font-semibold text-foreground", over && "text-destructive")}>{kg(packed)}</span> of{" "}
          {kg(limit)} kg
        </span>
      </div>
      <div
        className="relative h-2.5 overflow-hidden rounded-full bg-foreground/10"
        role="meter"
        aria-label="Bag weight"
        aria-valuemin={0}
        aria-valuemax={limit}
        aria-valuenow={Math.round(packed * 10) / 10}
        aria-valuetext={`${kg(packed)} of ${kg(limit)} kilograms`}
      >
        <div
          className="weight-fill weight-ghost absolute inset-0 rounded-full opacity-(--ghost-opacity)"
          style={{ "--fill": Math.min(1, plannedShare), "--warm": warmth(plannedShare) } as CSSProperties}
        />
        <div
          className={cn("weight-fill absolute inset-0 rounded-full", over && "is-over")}
          style={{ "--fill": Math.min(1, share), "--warm": warmth(share) } as CSSProperties}
        />
      </div>
      <p className={cn("text-xs text-muted-foreground tabular-nums", plannedOver && "text-destructive", compact && "sr-only")}>
        {plannedOver
          ? `Everything on the list comes to ${kg(planned)} kg, ${kg(planned - limit)} kg over.`
          : `Everything on the list comes to ${kg(planned)} kg.`}
      </p>
    </div>
  )
}
