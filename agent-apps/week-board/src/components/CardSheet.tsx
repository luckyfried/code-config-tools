import { useState } from "react"
import { Trash2 } from "lucide-react"
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { LATER, weekdayLong, weekdayShort, dayOfMonth, type DayKey, type WeekView } from "@/lib/dates"
import type { Task } from "@/lib/board"

interface Props {
  task: Task | null
  view: WeekView
  laterOn: boolean
  side: "right" | "bottom"
  onClose: () => void
  onEdit: (id: string, change: { title?: string; notes?: string }) => void
  onMove: (id: string, day: DayKey) => void
  onToggle: (id: string) => void
  onRemove: (id: string) => void
}

/** The card's own page: its words, its notes, which day it sits on, and the way to delete it. */
export function CardSheet({ task, view, laterOn, side, onClose, onEdit, onMove, onToggle, onRemove }: Props) {
  const [confirming, setConfirming] = useState(false)
  const targets: DayKey[] = [...view.days, ...(laterOn ? [LATER] : [])]
  return (
    <Sheet
      open={!!task}
      onOpenChange={(o) => {
        if (!o) {
          setConfirming(false)
          onClose()
        }
      }}
    >
      <SheetContent
        side={side}
        className={cn(
          "gap-0 bg-background",
          side === "bottom" ? "max-h-[88dvh] rounded-t-2xl pb-[env(safe-area-inset-bottom)]" : "w-full sm:max-w-md",
        )}
      >
        {task && (
          <>
            <SheetHeader className="pr-12">
              <SheetTitle className="text-base">
                {task.day === LATER ? "Later" : weekdayLong(task.day)}
                {task.done ? ", done" : ""}
              </SheetTitle>
              <SheetDescription>Changes save as you type.</SheetDescription>
            </SheetHeader>
            <div className="flex flex-col gap-5 overflow-y-auto px-4 pb-4">
              <label className="flex flex-col gap-1.5 text-sm font-medium">
                Task
                <Input
                  value={task.title}
                  onChange={(e) => onEdit(task.id, { title: e.target.value })}
                  onBlur={(e) => !e.target.value.trim() && onEdit(task.id, { title: "Untitled task" })}
                  className="h-11 text-base font-normal"
                />
              </label>
              <label className="flex flex-col gap-1.5 text-sm font-medium">
                Notes
                <Textarea
                  value={task.notes}
                  onChange={(e) => onEdit(task.id, { notes: e.target.value })}
                  placeholder="Numbers, links, the thing to remember."
                  className="min-h-28 text-base font-normal"
                />
              </label>
              <fieldset className="flex flex-col gap-2">
                <legend className="mb-1.5 text-sm font-medium">Move to</legend>
                <div className="grid grid-cols-4 gap-1.5">
                  {targets.map((k) => {
                    const here = task.day === k
                    const past = k !== LATER && k < view.anchor
                    return (
                      <button
                        key={k}
                        type="button"
                        aria-pressed={here}
                        disabled={past && !here}
                        onClick={() => onMove(task.id, k)}
                        className={cn(
                          "flex h-12 flex-col items-center justify-center rounded-lg border text-xs leading-tight outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40",
                          here ? "border-primary bg-primary text-primary-foreground" : "bg-card hover:bg-accent",
                        )}
                      >
                        {k === LATER ? (
                          <span className="text-sm font-medium">Later</span>
                        ) : (
                          <>
                            <span className="font-medium">{k === view.today ? "Today" : weekdayShort(k)}</span>
                            <span className="tabular-nums opacity-75">{dayOfMonth(k)}</span>
                          </>
                        )}
                      </button>
                    )
                  })}
                </div>
              </fieldset>
            </div>
            <SheetFooter className="flex-row items-center justify-between gap-2 border-t">
              {confirming ? (
                <div className="flex items-center gap-2">
                  <Button variant="destructive" className="h-10" onClick={() => onRemove(task.id)}>
                    Delete it
                  </Button>
                  <Button variant="ghost" className="h-10" onClick={() => setConfirming(false)}>
                    Keep
                  </Button>
                </div>
              ) : (
                <Button variant="ghost" className="h-10 gap-1.5 text-destructive" onClick={() => setConfirming(true)}>
                  <Trash2 className="size-4" aria-hidden />
                  Delete
                </Button>
              )}
              <Button className="h-10" variant={task.done ? "secondary" : "default"} onClick={() => onToggle(task.id)}>
                {task.done ? "Not done yet" : "Mark done"}
              </Button>
            </SheetFooter>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
