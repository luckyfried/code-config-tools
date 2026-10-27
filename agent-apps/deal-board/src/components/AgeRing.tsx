import { ageFraction, ageWarmth } from "@/lib/pipeline"
import { cn } from "@/lib/utils"

const R = 6.25
const C = 2 * Math.PI * R

/** How long a deal has sat in its stage: the ring fills over thirty days and stays neutral for a week, then warms to amber and to red. */
export function AgeRing({ days, className }: { days: number; className?: string }) {
  const { toWarm, toStale } = ageWarmth(days)
  const fill = Math.max(0.06, ageFraction(days))
  return (
    <svg
      viewBox="0 0 16 16"
      data-age-ring=""
      className={cn("size-4 shrink-0 -rotate-90", className)}
      style={{ "--to-warm": toWarm, "--to-stale": toStale } as React.CSSProperties}
      aria-hidden="true"
    >
      <circle cx="8" cy="8" r={R} fill="none" strokeWidth="2.5" className="stroke-age-track" />
      <circle cx="8" cy="8" r={R} fill="none" strokeWidth="2.5" strokeLinecap="round" stroke="var(--age)" strokeDasharray={`${fill * C} ${C}`} />
    </svg>
  )
}
