import { useDraggable } from "@dnd-kit/core"
import { memo } from "react"
import { ageFraction, ageWarmth, daysInStage, type Deal } from "@/lib/pipeline"
import { CompanyMark } from "@/components/CompanyMark"
import { dayLabel, money } from "@/lib/format"
import { cardRef } from "@/lib/motion"
import { cn } from "@/lib/utils"

interface CardProps {
  deal: Deal
  now: number
  lifted?: boolean
  className?: string
}

const R = 20
const C = 2 * Math.PI * R

/** The company's mark, ringed by its days in stage: the ring fills over thirty days and stays neutral for a week, then warms to amber and to red. */
export function AgedMark({ company, days }: { company: string; days: number }) {
  const { toWarm, toStale } = ageWarmth(days)
  const fill = Math.max(0.04, ageFraction(days))
  return (
    <span className="relative grid size-11 shrink-0 place-items-center">
      <svg viewBox="0 0 44 44" data-age-ring="" className="absolute inset-0 size-full -rotate-90" style={{ "--to-warm": toWarm, "--to-stale": toStale } as React.CSSProperties} aria-hidden="true">
        <circle cx="22" cy="22" r={R} fill="none" strokeWidth="2.5" className="stroke-age-track" />
        <circle cx="22" cy="22" r={R} fill="none" strokeWidth="2.5" strokeLinecap="round" stroke="var(--age)" strokeDasharray={`${fill * C} ${C}`} />
      </svg>
      <CompanyMark company={company} className="size-[34px] text-[15px]" />
    </span>
  )
}

/** One deal: the ringed mark, the company, the value in tabular figures (right-aligned beside the company on a phone; on a wide board, where columns are narrow, on its own line with the days in stage), and the whole next step, wrapping where the column is narrow (after the days in stage on a phone). */
export const DealFace = memo(function DealFace({ deal, now, lifted, className }: CardProps) {
  const days = daysInStage(deal, now)
  return (
    <div
      className={cn(
        "deal-face flex w-full items-center gap-3 rounded-[14px] border border-card-border py-2.5 pr-3 pl-2.5 text-left text-card-foreground transition-[box-shadow,transform] duration-200 ease-out",
        lifted && "rotate-[-1.5deg] scale-[1.04] shadow-lift!",
        className,
      )}
    >
      <AgedMark company={deal.company} days={days} />
      <span className="flex min-w-0 flex-1 flex-col gap-0.5">
        <span className="flex items-baseline gap-2 leading-snug">
          <span className="min-w-0 flex-1 truncate text-[15px] font-semibold tracking-[-0.01em]">{deal.company}</span>
          <span className="shrink-0 text-base font-semibold tracking-[-0.01em] text-headline tabular-nums lg:hidden">{money(deal.value)}</span>
        </span>
        <span className="flex items-baseline gap-2 max-lg:hidden">
          <span className="text-[17px] font-semibold leading-tight tracking-[-0.015em] text-headline tabular-nums">{money(deal.value)}</span>
          <span className="ml-auto text-[13px] font-semibold text-foreground/60 tabular-nums">{days}d</span>
        </span>
        <span className="text-[13px] leading-snug text-balance break-words text-muted-foreground">
          <span className="font-semibold text-foreground/75 tabular-nums lg:hidden">{days}d</span>
          <span className="mx-1.5 text-foreground/25 lg:hidden">·</span>
          {deal.nextStep || "No next step"}
          {deal.date ? <> <span className="whitespace-nowrap">by {dayLabel(deal.date)}</span></> : null}
        </span>
      </span>
    </div>
  )
})

/** A card on the board: drags to another stage, and opens the deal sheet on a click or a tap. */
export function DealCard({ deal, now, onOpen, dimmed }: { deal: Deal; now: number; onOpen: (id: string) => void; dimmed: boolean }) {
  const { attributes, listeners, setNodeRef } = useDraggable({ id: deal.id, data: { deal } })
  const register = cardRef(deal.id)
  const days = daysInStage(deal, now)
  return (
    <button
      type="button"
      ref={(el) => {
        setNodeRef(el)
        return register(el)
      }}
      data-deal={deal.id}
      {...attributes}
      {...listeners}
      aria-roledescription="deal card"
      aria-label={`${deal.company}, ${money(deal.value)}, ${days} ${days === 1 ? "day" : "days"} in this stage. Next step: ${deal.nextStep || "none"}.`}
      title={`${days} ${days === 1 ? "day" : "days"} in this stage`}
      onClick={() => onOpen(deal.id)}
      onContextMenu={(event) => event.preventDefault()}
      className={cn(
        "deal-card no-callout block w-full touch-manipulation rounded-xl outline-none transition-[opacity,transform] duration-150 ease-out focus-visible:ring-3 focus-visible:ring-ring/60 active:scale-[0.985]",
        dimmed && "opacity-35",
      )}
    >
      <DealFace deal={deal} now={now} className="pointer-coarse:py-3" />
    </button>
  )
}
