import { format, isToday, parseISO } from "date-fns"
import { cn } from "@/lib/utils"
import { dayKey, fmtInt, recordDates, setsOf, type LiftSet } from "@/lib/lift"
import { useLog } from "@/lib/log-context"

/** The last few days trained before today: the lifts, the sets, the weight moved, and any records. */
export function RecentSessions({ count = 5, className }: { count?: number; className?: string }) {
  const log = useLog()
  const days = new Map<string, LiftSet[]>()
  for (const s of log.sets) {
    if (isToday(parseISO(s.date))) continue
    const k = dayKey(s.date)
    days.set(k, [...(days.get(k) ?? []), s])
  }
  const recent = [...days.entries()].sort((a, b) => (a[0] < b[0] ? 1 : -1)).slice(0, count)
  if (!recent.length) return null
  const records = new Set(log.exercises.flatMap((e) => [...recordDates(setsOf(log.sets, e.id))]))
  return (
    <section className={cn("flex flex-col gap-2", className)} aria-label="Recent sessions">
      <h3 className="px-1 text-sm font-medium text-muted-foreground">Recent sessions</h3>
      <ul className="surface flex flex-col overflow-hidden rounded-2xl">
        {recent.map(([key, list]) => {
          const lifts = [...new Set(list.map((s) => s.exercise))]
          const prs = list.filter((s) => records.has(s.date)).length
          const moved = list.reduce((n, s) => n + s.weight * s.reps, 0)
          return (
            <li key={key} className="border-b last:border-b-0">
              <button
                type="button"
                onClick={() => log.select(lifts[0])}
                className="grid min-h-16 w-full grid-cols-[4.5rem_minmax(0,1fr)_auto] items-center gap-3 px-4 py-2.5 text-left hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
              >
                <span className="flex flex-col leading-tight">
                  <span className="text-sm text-muted-foreground">{format(parseISO(list[0].date), "EEE")}</span>
                  <span className="font-semibold">{format(parseISO(list[0].date), "MMM d")}</span>
                </span>
                <span className="min-w-0">
                  <span className="block truncate font-medium">{lifts.map((id) => log.exerciseById.get(id)?.label ?? id).join(", ")}</span>
                  <span className="figures block text-sm text-muted-foreground">
                    {list.length} sets, {fmtInt(moved)} {log.units} moved
                  </span>
                </span>
                {prs ? (
                  <span className="pr-chip inline-flex h-6 items-center rounded-full px-2 text-xs font-bold">
                    {prs} PR{prs > 1 ? "s" : ""}
                  </span>
                ) : (
                  <span />
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
