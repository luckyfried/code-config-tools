import { cn } from "@/lib/utils"
import { bestE1rm, dayKey, e1rm, fmtE1rm, fmtWeight } from "@/lib/lift"
import { useLog } from "@/lib/log-context"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { E1rmChart } from "./E1rmChart"

/** The selected lift's strength curve with its best numbers above it. */
export function ChartCard({ height = 240, className }: { height?: number; className?: string }) {
  const log = useLog()
  const { selectedSets: sets, selected, units } = log
  const best = bestE1rm(sets)
  const top = sets.reduce<(typeof sets)[number] | null>((a, b) => (!a || e1rm(b.weight, b.reps) > e1rm(a.weight, a.reps) ? b : a), null)
  const heaviest = sets.reduce((m, s) => Math.max(m, s.weight), 0)
  const sessions = new Set(sets.map((s) => dayKey(s.date))).size
  const stat = (label: React.ReactNode, value: string, unit?: string) => (
    <div className="min-w-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="figures truncate text-xl font-semibold tracking-tight">
        {value}
        {unit ? <span className="text-sm font-normal text-muted-foreground"> {unit}</span> : null}
      </dd>
    </div>
  )
  return (
    <section className={cn("surface flex flex-col gap-3 rounded-2xl p-4", className)} aria-label={`${selected.label} strength curve`}>
      <header className="flex items-baseline justify-between gap-3">
        <h2 className="truncate text-lg font-semibold">{selected.label}</h2>
        <span className="shrink-0 text-sm text-muted-foreground">Estimated one-rep max</span>
      </header>
      <dl className="grid grid-cols-3 gap-3">
        {stat(
          <TooltipProvider delayDuration={150}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="cursor-help rounded-sm underline decoration-dotted underline-offset-2 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
                >
                  Best e1RM
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" sideOffset={6}>
                Epley: e1RM = weight × (1 + reps ÷ 30)
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>,
          best ? fmtE1rm(best) : "None", best ? units : undefined)}
        {stat("Best set", top ? `${fmtWeight(top.weight)} × ${top.reps}` : "None")}
        {stat("Heaviest", heaviest ? fmtWeight(heaviest) : "None", heaviest ? units : undefined)}
      </dl>
      <E1rmChart key={selected.id} sets={sets} label={selected.label} units={units} height={height} />
      <p className="text-xs text-muted-foreground">
        {sessions} {sessions === 1 ? "session" : "sessions"}, {sets.length} {sets.length === 1 ? "set" : "sets"}. Each point is a session’s best set; gold marks a record.
      </p>
    </section>
  )
}
