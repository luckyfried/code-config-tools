import { minutesText } from "@/lib/durations"
import { cn } from "@/lib/utils"

const RINGS = [13, 9, 5]

/** Total time as a clock face: each ring is an hour, filled as far as the recipe runs. */
export function TimeArc({ minutes, className, label = true }: { minutes: number; className?: string; label?: boolean }) {
  const laps = RINGS.map((_, index) => Math.max(0, Math.min(1, (minutes - index * 60) / 60)))
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm nums", className)}>
      <svg viewBox="0 0 32 32" className="size-8 shrink-0 -rotate-90" aria-hidden="true">
        {RINGS.map((r, index) =>
          index === 0 || laps[index] > 0 ? (
            <g key={r}>
              <circle cx="16" cy="16" r={r} fill="none" strokeWidth="2.5" className="stroke-foreground/12" />
              <circle
                cx="16"
                cy="16"
                r={r}
                fill="none"
                strokeWidth="2.5"
                strokeLinecap="round"
                pathLength={100}
                strokeDasharray={`${laps[index] * 100} 100`}
                className="stroke-primary"
              />
            </g>
          ) : null,
        )}
      </svg>
      {label ? <span>{minutesText(minutes)}</span> : <span className="sr-only">{minutesText(minutes)}</span>}
    </span>
  )
}
