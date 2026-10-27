import { useState } from "react"
import { format, parseISO } from "date-fns"
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
import { cn } from "@/lib/utils"
import { fmtWeight, type LiftSet } from "@/lib/lift"
import { removeSet } from "@/lib/store"

type Props = { set: LiftSet; units: string; record: boolean; fresh?: boolean; label: string; editable: boolean }

/** One set on today's row; a tap offers to take it off the log. */
export function SetChip({ set, units, record, fresh, label, editable }: Props) {
  const [open, setOpen] = useState(false)
  const text = (
    <>
      <span className="figures font-semibold">{fmtWeight(set.weight)}</span>
      <span className="text-muted-foreground">×</span>
      <span className="figures font-semibold">{set.reps}</span>
      {record ? <span className="pr-dot ml-0.5 size-1.5 rounded-full" aria-label="record" /> : null}
    </>
  )
  const chip = cn(
    "inline-flex h-9 shrink-0 items-center gap-1 rounded-full bg-secondary px-2.5 text-sm text-secondary-foreground sm:px-3",
    fresh && "set-in",
  )
  if (!editable) return <span className={chip}>{text}</span>
  return (
    <>
      <button type="button" className={cn(chip, "press hover:bg-accent")} onClick={() => setOpen(true)} aria-label={`${fmtWeight(set.weight)} ${units} for ${set.reps}, logged ${format(parseISO(set.date), "h:mm a")}`}>
        {text}
      </button>
      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent size="sm">
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this set?</AlertDialogTitle>
            <AlertDialogDescription>
              {label}, {fmtWeight(set.weight)} {units} for {set.reps}, logged at {format(parseISO(set.date), "h:mm a")}.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => removeSet(set)}>
              Delete set
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
