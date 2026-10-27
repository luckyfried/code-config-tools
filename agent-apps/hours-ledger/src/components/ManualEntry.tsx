import { useState } from "react"
import { CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from "@/components/ui/drawer"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { config, weekStartsOn } from "@/lib/config"
import { useMedia } from "@/lib/hooks"
import { addEntry, useLedger } from "@/lib/store"
import { HOUR, MINUTE, format, hm } from "@/lib/time"

// "1:30", "1.5", "90m", or "2h" as milliseconds; NaN when it does not read as a duration.
export function parseDuration(text: string): number {
  const t = text.trim().toLowerCase()
  let m = t.match(/^(\d+):([0-5]?\d)$/)
  if (m) return Number(m[1]) * HOUR + Number(m[2]) * MINUTE
  m = t.match(/^(\d+(?:\.\d+)?)\s*m(in)?$/)
  if (m) return Number(m[1]) * MINUTE
  m = t.match(/^(\d+(?:\.\d+)?)\s*h?$/)
  if (m) return Number(m[1]) * HOUR
  return NaN
}

function at(day: Date, time: string): number {
  const [h, m] = time.split(":").map(Number)
  const d = new Date(day)
  d.setHours(h, m, 0, 0)
  return d.getTime()
}

export function ManualEntry({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const desktop = useMedia("(min-width: 768px)")
  const body = <EntryForm key={String(open)} onDone={() => onOpenChange(false)} />
  if (desktop) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add time</DialogTitle>
            <DialogDescription>A duration or a start and end time, on any day.</DialogDescription>
          </DialogHeader>
          {body}
        </DialogContent>
      </Dialog>
    )
  }
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent>
        <DrawerHeader className="text-left">
          <DrawerTitle>Add time</DrawerTitle>
          <DrawerDescription>A duration or a start and end time, on any day.</DrawerDescription>
        </DrawerHeader>
        <div className="px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">{body}</div>
      </DrawerContent>
    </Drawer>
  )
}

function EntryForm({ onDone }: { onDone: () => void }) {
  const ledger = useLedger()
  const [clientId, setClientId] = useState(ledger.lastClientId ?? config.clients[0].id)
  const [day, setDay] = useState<Date>(() => new Date())
  const [mode, setMode] = useState<"duration" | "range">("duration")
  const [duration, setDuration] = useState("1:00")
  const [from, setFrom] = useState("09:00")
  const [to, setTo] = useState("10:00")
  const [note, setNote] = useState("")
  const [dayOpen, setDayOpen] = useState(false)

  let start = NaN
  let end = NaN
  if (mode === "duration") {
    const ms = parseDuration(duration)
    const isToday = format(day, "yyyy-MM-dd") === format(Date.now(), "yyyy-MM-dd")
    end = isToday ? Date.now() : at(day, "17:00")
    start = end - ms
  } else {
    start = at(day, from)
    end = at(day, to)
    if (end <= start) end += 24 * HOUR
  }
  const valid = Number.isFinite(start) && Number.isFinite(end) && end > start
  const problem = mode === "duration" && !Number.isFinite(parseDuration(duration)) ? "Write the time as 1:30, 1.5, or 90m." : null

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!valid) return
    addEntry({ start, end, clientId, note })
    onDone()
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="flex flex-col gap-2">
          <Label htmlFor="manual-client">Client</Label>
          <Select value={clientId} onValueChange={setClientId}>
            <SelectTrigger id="manual-client" className="h-11 w-full text-base data-[size=default]:h-11">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {config.clients.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-2">
          <Label htmlFor="manual-day">Day</Label>
          <Popover open={dayOpen} onOpenChange={setDayOpen}>
            <PopoverTrigger asChild>
              <Button id="manual-day" variant="outline" className="h-11 justify-start font-normal">
                <CalendarIcon data-icon="inline-start" />
                {format(day, "EEE, MMM d")}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar
                mode="single"
                selected={day}
                weekStartsOn={weekStartsOn}
                onSelect={(d) => {
                  if (d) setDay(d)
                  setDayOpen(false)
                }}
              />
            </PopoverContent>
          </Popover>
        </div>
      </div>

      <ToggleGroup
        type="single"
        variant="outline"
        value={mode}
        onValueChange={(v) => v && setMode(v as "duration" | "range")}
        className="w-full"
      >
        <ToggleGroupItem value="duration" className="h-10 flex-1">
          Duration
        </ToggleGroupItem>
        <ToggleGroupItem value="range" className="h-10 flex-1">
          Start and end
        </ToggleGroupItem>
      </ToggleGroup>

      {mode === "duration" ? (
        <div className="flex flex-col gap-2">
          <Label htmlFor="manual-duration">How long</Label>
          <Input
            id="manual-duration"
            inputMode="decimal"
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            aria-invalid={problem ? true : undefined}
            className="h-11 font-mono text-base tnum md:text-base"
          />
          {problem ? <p className="text-sm text-destructive">{problem}</p> : null}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3">
          <div className="flex flex-col gap-2">
            <Label htmlFor="manual-from">Start</Label>
            <Input id="manual-from" type="time" value={from} onChange={(e) => setFrom(e.target.value)} className="h-11 font-mono text-base md:text-base" />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="manual-to">End</Label>
            <Input id="manual-to" type="time" value={to} onChange={(e) => setTo(e.target.value)} className="h-11 font-mono text-base md:text-base" />
          </div>
        </div>
      )}

      <div className="flex flex-col gap-2">
        <Label htmlFor="manual-note">Note</Label>
        <Input id="manual-note" value={note} placeholder="What was it for?" onChange={(e) => setNote(e.target.value)} className="h-11 text-base md:text-base" />
      </div>

      <DialogFooterOrPlain>
        <Button type="submit" size="lg" className="h-11 w-full text-base" disabled={!valid}>
          Add {valid ? hm(end - start) : ""}
        </Button>
      </DialogFooterOrPlain>
    </form>
  )
}

function DialogFooterOrPlain({ children }: { children: React.ReactNode }) {
  const desktop = useMedia("(min-width: 768px)")
  return desktop ? <DialogFooter>{children}</DialogFooter> : <DrawerFooter className="px-0">{children}</DrawerFooter>
}
