import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { useLedger } from "@/lib/store"
import { entriesOnDay, format, hm, msOnDay, useNow } from "@/lib/time"
import { EntryRow } from "./EntryRow"

// The entries of one day, opened from a bar or a day of the strip; every entry edits in place.
export function DayDialog({ day, onClose }: { day: Date | null; onClose: () => void }) {
  const ledger = useLedger()
  const now = useNow(1000)
  const list = day ? entriesOnDay(ledger.entries, day, now) : []
  const total = day ? list.reduce((sum, e) => sum + msOnDay(e, day, now), 0) : 0
  return (
    <Dialog open={day !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{day ? format(day, "EEEE, MMMM d") : ""}</DialogTitle>
          <DialogDescription className="font-mono tnum">
            {list.length === 0 ? "No hours on this day." : `${hm(total)} across ${list.length} ${list.length === 1 ? "entry" : "entries"}`}
          </DialogDescription>
        </DialogHeader>
        {list.length > 0 ? (
          <ul className="-mx-1 max-h-[60dvh] overflow-y-auto px-1">
            {list.map((e) => (
              <EntryRow key={e.id} entry={e} now={now} />
            ))}
          </ul>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
