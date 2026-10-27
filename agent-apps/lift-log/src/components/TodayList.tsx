import { ChevronRightIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { e1rm, fmtWeight } from "@/lib/lift"
import { useLog } from "@/lib/log-context"

/** Every lift done today, with its best set; a tap brings it back to the steppers. */
export function TodayList({ className }: { className?: string }) {
  const log = useLog()
  const groups = new Map<string, typeof log.todaySets>()
  for (const s of log.todaySets) groups.set(s.exercise, [...(groups.get(s.exercise) ?? []), s])
  if (groups.size === 0) return null
  return (
    <section className={cn("flex flex-col gap-2", className)} aria-label="Today">
      <h3 className="px-1 text-sm font-medium text-muted-foreground">Today</h3>
      <ul className="surface flex flex-col overflow-hidden rounded-2xl">
        {[...groups.entries()].map(([id, list]) => {
          const ex = log.exerciseById.get(id)
          const top = list.reduce((a, b) => (e1rm(b.weight, b.reps) > e1rm(a.weight, a.reps) ? b : a))
          const current = id === log.selected.id
          return (
            <li key={id} className="border-b last:border-b-0">
              <button
                type="button"
                onClick={() => log.select(id)}
                aria-current={current ? "true" : undefined}
                className="flex min-h-14 w-full items-center gap-3 px-4 py-2 text-left hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
              >
                <span className={cn("size-2 shrink-0 rounded-full", current ? "bg-primary" : "bg-transparent")} />
                <span className="min-w-0 flex-1 truncate font-medium">{ex?.label ?? id}</span>
                <span className="figures text-sm text-muted-foreground">
                  {list.length} {list.length === 1 ? "set" : "sets"}, top {fmtWeight(top.weight)} × {top.reps}
                </span>
                <ChevronRightIcon className="size-4 text-muted-foreground" />
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
