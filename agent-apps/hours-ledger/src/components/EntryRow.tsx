import { TrashIcon } from "lucide-react"
import { cn } from "cn"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { clientById, clientColor, config } from "@/lib/config"
import { deleteEntry, justDropped, updateEntry, type Entry } from "@/lib/store"
import { HOUR, durationMs, format, hm } from "@/lib/time"

// Sets the clock time of a timestamp and keeps its date.
function withTime(base: number, value: string): number {
  const [h, m] = value.split(":").map(Number)
  const d = new Date(base)
  d.setHours(h, m, 0, 0)
  return d.getTime()
}

export function EntryRow({ entry, now }: { entry: Entry; now: number }) {
  const live = entry.end === null
  const ms = durationMs(entry, now)
  const long = ms > 12 * HOUR
  const client = clientById(entry.clientId)

  const setStart = (v: string) => {
    if (!v) return
    const start = withTime(entry.start, v)
    updateEntry(entry.id, { start: entry.end !== null && start >= entry.end ? entry.end - 60_000 : start })
  }
  const setEnd = (v: string) => {
    if (!v || entry.end === null) return
    let end = withTime(entry.start, v)
    if (end <= entry.start) end += 24 * HOUR
    updateEntry(entry.id, { end })
  }

  return (
    <li
      style={{ "--c": clientColor(entry.clientId) } as React.CSSProperties}
      className={cn(
        "group grid grid-cols-[4px_minmax(0,1fr)_auto_auto] items-center gap-x-3 gap-y-2 border-b border-rule py-3 last:border-b-0 sm:grid-cols-[4px_minmax(0,1fr)_auto_auto_auto]",
        justDropped(entry.id) && "drop-in",
      )}
    >
      <span className="row-span-2 h-full min-h-10 w-1 rounded-full bg-(--c) sm:row-span-1" aria-hidden />
      <div className="flex min-w-0 flex-col">
        <Input
          aria-label={`Note for ${client.name}`}
          value={entry.note}
          placeholder="Add a note"
          onChange={(e) => updateEntry(entry.id, { note: e.target.value })}
          className="h-8 border-transparent bg-transparent px-1.5 text-base font-medium shadow-none hover:border-input md:text-sm dark:bg-transparent"
        />
        <div className="flex items-center gap-2 px-1.5">
          <Select value={entry.clientId} onValueChange={(v) => updateEntry(entry.id, { clientId: v })}>
            <SelectTrigger
              aria-label="Client"
              size="sm"
              className="h-6 border-0 bg-transparent px-0 text-xs text-muted-foreground shadow-none dark:bg-transparent"
            >
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
          {long ? <Badge variant="destructive">Over 12 h</Badge> : null}
        </div>
      </div>
      <div className="col-span-3 col-start-2 row-start-2 flex items-center gap-1.5 sm:col-span-1 sm:col-start-auto sm:row-start-auto">
        <Input
          type="time"
          aria-label="Start"
          value={format(entry.start, "HH:mm")}
          onChange={(e) => setStart(e.target.value)}
          className="h-9 min-w-0 flex-1 px-2 font-mono text-sm tnum sm:w-[7.5rem] sm:flex-none md:text-sm"
        />
        <span className="text-muted-foreground" aria-hidden>
          –
        </span>
        {live ? (
          <span className="flex h-9 min-w-0 flex-1 items-center gap-2 sm:w-[7.5rem] sm:flex-none px-2 font-mono text-sm text-muted-foreground">
            <span className="breathe size-2 rounded-full bg-(--c)" aria-hidden />
            now
          </span>
        ) : (
          <Input
            type="time"
            aria-label="End"
            value={format(entry.end as number, "HH:mm")}
            onChange={(e) => setEnd(e.target.value)}
            className="h-9 min-w-0 flex-1 px-2 font-mono text-sm tnum sm:w-[7.5rem] sm:flex-none md:text-sm"
          />
        )}
      </div>
      <span className="col-start-3 row-start-1 w-14 text-right font-mono text-base font-medium tnum sm:col-start-auto sm:row-start-auto">
        {hm(ms)}
      </span>
      <Button
        variant="ghost"
        size="icon"
        aria-label="Delete entry"
        disabled={live}
        onClick={() => deleteEntry(entry.id)}
        className="col-start-4 row-start-1 justify-self-end text-muted-foreground sm:col-start-auto sm:row-start-auto"
      >
        <TrashIcon />
      </Button>
    </li>
  )
}
