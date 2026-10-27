import { useRef, useState } from "react"
import { format, parseISO } from "date-fns"
import { BellIcon, BellOffIcon, DownloadIcon, MinusIcon, PlusIcon, UploadIcon } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Toggle } from "@/components/ui/toggle"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { cn } from "@/lib/utils"
import type { Units } from "@/lib/config"
import { convert, isSet, type LiftSet } from "@/lib/lift"
import { useLog } from "@/lib/log-context"
import { clearSets, convertSets, importSets, ownSets, setPrefs } from "@/lib/store"

const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`

function Row({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 py-3">
      <div className="min-w-0">
        <p className="font-medium">{title}</p>
        {hint ? <p className="text-sm text-pretty text-muted-foreground">{hint}</p> : null}
      </div>
      {children}
    </div>
  )
}

/** Units, rest, the chime, and moving the log in and out of this browser. */
export function SettingsPanel({ className }: { className?: string }) {
  const log = useLog()
  const { units, restSeconds, chimeOn } = log
  const own = ownSets()
  const file = useRef<HTMLInputElement>(null)
  const [status, setStatus] = useState<string | null>(null)

  const changeUnits = (next: string) => {
    if (next !== "kg" && next !== "lb") return
    if (next === units) return
    convertSets(units, next)
    setPrefs({ units: next })
    setStatus(own.length ? `Your sets are now in ${next === "kg" ? "kilograms" : "pounds"}.` : null)
  }

  const exportLog = () => {
    const body = JSON.stringify({ app: "lift-log", units, exported: new Date().toISOString(), sets: own }, null, 2)
    const url = URL.createObjectURL(new Blob([body], { type: "application/json" }))
    const a = document.createElement("a")
    a.href = url
    a.download = `lift-log-${format(new Date(), "yyyy-MM-dd")}.json`
    document.body.append(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    setStatus(`Saved ${own.length} ${own.length === 1 ? "set" : "sets"} to a file.`)
  }

  const importLog = async (f: File) => {
    try {
      const data: unknown = JSON.parse(await f.text())
      const list = Array.isArray(data) ? data : (data as { sets?: unknown })?.sets
      const from = (data as { units?: unknown })?.units === "lb" ? "lb" : (data as { units?: unknown })?.units === "kg" ? "kg" : units
      if (!Array.isArray(list)) throw new Error("no sets")
      const sets: LiftSet[] = list.filter(isSet).map((s) => ({ date: s.date, exercise: s.exercise, weight: convert(s.weight, from as Units, units), reps: s.reps }))
      if (!sets.length) throw new Error("no sets")
      const added = importSets(sets)
      setStatus(added ? `Added ${added} ${added === 1 ? "set" : "sets"} from ${f.name}.` : `Every set in ${f.name} is already here.`)
    } catch {
      setStatus(`${f.name} has no sets Lift Log can read.`)
    }
  }

  const since = own.length ? format(parseISO(own.reduce((a, b) => (a.date < b.date ? a : b)).date), "MMMM d, yyyy") : null

  return (
    <section className={cn("surface flex flex-col rounded-2xl px-4", className)} aria-label="Settings">
      <Row title="Units" hint="Changing them converts every set.">
        <ToggleGroup type="single" value={units} onValueChange={changeUnits} variant="outline" spacing={0} aria-label="Units">
          <ToggleGroupItem value="kg" className="h-11 min-w-16 text-base">
            kg
          </ToggleGroupItem>
          <ToggleGroupItem value="lb" className="h-11 min-w-16 text-base">
            lb
          </ToggleGroupItem>
        </ToggleGroup>
      </Row>
      <Separator />
      <Row title="Rest between sets" hint="The bar across the top drains over this long.">
        <div className="flex items-center gap-1 rounded-xl bg-surface-2 p-1 ring-1 ring-border">
          <Button variant="secondary" size="icon" className="size-11" aria-label="Shorter rest" onClick={() => setPrefs({ restSeconds: Math.max(15, restSeconds - 15) })}>
            <MinusIcon />
          </Button>
          <span className="figures w-16 text-center text-lg font-semibold" aria-live="polite">
            {clock(restSeconds)}
          </span>
          <Button variant="secondary" size="icon" className="size-11" aria-label="Longer rest" onClick={() => setPrefs({ restSeconds: Math.min(600, restSeconds + 15) })}>
            <PlusIcon />
          </Button>
        </div>
      </Row>
      <Separator />
      <Row title="Chime" hint="Two tones when the rest is up.">
        <Toggle variant="outline" pressed={chimeOn} onPressedChange={(p) => setPrefs({ chime: p })} className="h-11 min-w-24 text-base" aria-label="Chime at the end of a rest">
          {chimeOn ? <BellIcon data-icon="inline-start" /> : <BellOffIcon data-icon="inline-start" />}
          {chimeOn ? "On" : "Off"}
        </Toggle>
      </Row>
      <Separator />
      <Row title="Your log" hint={since ? `${own.length} ${own.length === 1 ? "set" : "sets"} since ${since}, kept in this browser.` : "Nothing logged in this browser yet."}>
        <div className="flex gap-2">
          <Button variant="outline" className="h-11 px-4 text-base" onClick={exportLog} disabled={!own.length}>
            <DownloadIcon data-icon="inline-start" />
            Export
          </Button>
          <Button variant="outline" className="h-11 px-4 text-base" onClick={() => file.current?.click()}>
            <UploadIcon data-icon="inline-start" />
            Import
          </Button>
          <input
            ref={file}
            type="file"
            accept="application/json,.json"
            className="sr-only"
            tabIndex={-1}
            aria-label="Choose a Lift Log file"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void importLog(f)
              e.target.value = ""
            }}
          />
        </div>
      </Row>
      {status ? (
        <p className="-mt-1 pb-3 text-sm text-pretty" role="status">
          {status}
        </p>
      ) : null}
      <Separator />
      <Row title="Start over" hint="Takes every set off this browser.">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" className="h-11 px-4 text-base" disabled={!own.length}>
              Clear the log
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent size="sm">
            <AlertDialogHeader>
              <AlertDialogTitle>Clear every set?</AlertDialogTitle>
              <AlertDialogDescription>
                {own.length} {own.length === 1 ? "set goes" : "sets go"} from this browser. Export first to keep a copy.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Keep them</AlertDialogCancel>
              <AlertDialogAction
                variant="destructive"
                onClick={() => {
                  clearSets()
                  setStatus("The log is empty.")
                }}
              >
                Clear the log
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Row>
    </section>
  )
}
