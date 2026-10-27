import { useState } from "react"
import { format, parseISO } from "date-fns"
import { Trash2Icon } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { dayKey, e1rm, fmtE1rm, fmtWeight, recordDates, type LiftSet } from "@/lib/lift"
import { useLog } from "@/lib/log-context"
import { removeSet } from "@/lib/store"

/** The selected lift's sets by date, newest first, each with its estimated max. */
export function HistoryList() {
  const log = useLog()
  const { selectedSets, units } = log
  const records = recordDates(selectedSets)
  const [doomed, setDoomed] = useState<LiftSet | null>(null)
  const days: { key: string; sets: LiftSet[] }[] = []
  for (const s of [...selectedSets].reverse()) {
    const k = dayKey(s.date)
    if (days.at(-1)?.key === k) days.at(-1)!.sets.push(s)
    else days.push({ key: k, sets: [s] })
  }
  if (!days.length) return null
  return (
    <div className="flex flex-col gap-4">
      {days.map((d) => {
        const ordered = [...d.sets].reverse()
        return (
          <section key={d.key} aria-label={format(parseISO(d.sets[0].date), "EEEE, MMMM d")}>
            <h3 className="flex items-baseline justify-between px-1 pb-1.5 text-sm">
              <span className="font-medium">{format(parseISO(d.sets[0].date), "EEE, MMM d")}</span>
              <span className="figures text-muted-foreground">
                {d.sets.length} {d.sets.length === 1 ? "set" : "sets"}
              </span>
            </h3>
            <ol className="surface overflow-hidden rounded-xl">
              {ordered.map((s, i) => (
                <li key={s.date} className="flex min-h-12 items-center gap-3 border-b px-4 last:border-b-0">
                  <span className="figures w-5 text-sm text-muted-foreground">{i + 1}</span>
                  <span className="figures flex-1 text-base">
                    <span className="font-semibold">{fmtWeight(s.weight)}</span> {units} × <span className="font-semibold">{s.reps}</span>
                  </span>
                  {records.has(s.date) ? (
                    <span className="pr-chip inline-flex h-5 items-center rounded-full px-1.5 text-xs font-bold">PR</span>
                  ) : null}
                  <span className="figures w-16 text-right text-sm text-muted-foreground">{fmtE1rm(e1rm(s.weight, s.reps))}</span>
                  {log.sample ? null : (
                    <Button variant="ghost" size="icon" className="-mr-2 size-11 text-muted-foreground" aria-label="Delete this set" onClick={() => setDoomed(s)}>
                      <Trash2Icon />
                    </Button>
                  )}
                </li>
              ))}
            </ol>
          </section>
        )
      })}
      <AlertDialog open={doomed !== null} onOpenChange={(o) => !o && setDoomed(null)}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this set?</AlertDialogTitle>
            <AlertDialogDescription>
              {doomed ? `${log.selected.label}, ${fmtWeight(doomed.weight)} ${units} for ${doomed.reps} on ${format(parseISO(doomed.date), "MMMM d")}.` : ""}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => doomed && removeSet(doomed)}>
              Delete set
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
