import { useMemo, useRef, useState, type FormEvent } from "react"
import { CalendarDays, CornerDownLeft, Inbox } from "lucide-react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { LATER, weekdayLong, type DayKey, type WeekView } from "@/lib/dates"
import { parseLine } from "@/lib/parse"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  view: WeekView
  laterOn: boolean
  defaultDay: DayKey
  onAdd: (title: string, day: DayKey) => void
}

function dayName(k: DayKey, view: WeekView): string {
  if (k === LATER) return "Later"
  if (k === view.today) return "Today"
  return weekdayLong(k)
}

/** One field: the task, with an optional day word at the end that is read before the card is added. */
export function AddDialog({ open, onOpenChange, view, laterOn, defaultDay, onAdd }: Props) {
  const [text, setText] = useState("")
  const [added, setAdded] = useState<string | null>(null)
  const input = useRef<HTMLInputElement>(null)
  const parsed = useMemo(() => parseLine(text, view, laterOn), [text, view, laterOn])
  const target = parsed.target ?? defaultDay
  const title = parsed.title

  function submit(e: FormEvent) {
    e.preventDefault()
    if (!title) return
    onAdd(title, target)
    setAdded(`Added to ${dayName(target, view)}.`)
    setText("")
    input.current?.focus()
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        onOpenChange(o)
        if (!o) {
          setText("")
          setAdded(null)
        }
      }}
    >
      <DialogContent className="top-[max(1rem,env(safe-area-inset-top))] translate-y-0 gap-3 p-4 sm:top-[18vh] sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-base">Add a task</DialogTitle>
          <DialogDescription>
            End with a day to place it: today, tomorrow, mon to sun{laterOn ? ", or later" : ""}.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex flex-col gap-3">
          <Input
            ref={input}
            autoFocus
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              setAdded(null)
            }}
            placeholder="Call the bank fri"
            aria-label="Task"
            enterKeyHint="done"
            autoComplete="off"
            className="h-12 text-base"
          />
          <div className="flex items-center justify-between gap-3">
            <span
              className="inline-flex h-8 items-center gap-1.5 rounded-full border bg-secondary whitespace-nowrap px-3 text-sm font-medium text-secondary-foreground"
              aria-live="polite"
            >
              {target === LATER ? <Inbox className="size-4" aria-hidden /> : <CalendarDays className="size-4" aria-hidden />}
              {dayName(target, view)}
            </span>
            <Button type="submit" disabled={!title} className="h-10 gap-1.5 px-4">
              Add
              <CornerDownLeft className="size-4" aria-hidden />
            </Button>
          </div>
          <p className="min-h-5 text-sm text-muted-foreground" aria-live="polite">
            {added}
          </p>
        </form>
      </DialogContent>
    </Dialog>
  )
}
