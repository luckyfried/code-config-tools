import { useRef, useState } from "react"
import { DownloadIcon, UploadIcon } from "lucide-react"
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
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Panel } from "@/components/Panel"
import { clientColor, config, money } from "@/lib/config"
import { exportCsv, exportJson, parseImport } from "@/lib/exporters"
import { clearEntries, effectiveRounding, importEntries, setRounding, useLedger } from "@/lib/store"
import { format } from "@/lib/time"

export function SettingsView() {
  const ledger = useLedger()
  const rounding = effectiveRounding(ledger)
  const file = useRef<HTMLInputElement>(null)
  const [message, setMessage] = useState<string | null>(null)
  const finished = ledger.entries.filter((e) => e.end !== null)
  const first = finished.reduce((m, e) => Math.min(m, e.start), Infinity)

  const onImport = async (f: File | undefined) => {
    if (!f) return
    try {
      const added = importEntries(parseImport(await f.text()))
      setMessage(added ? `Imported ${added} ${added === 1 ? "entry" : "entries"}.` : "Every entry in that file is already here.")
    } catch {
      setMessage("That file is not an Hours Ledger export. Pick the .json file Export JSON wrote.")
    }
    if (file.current) file.current.value = ""
  }

  return (
    <div className="grid gap-4 sm:gap-5 lg:grid-cols-3 xl:gap-6">
      <Panel title="Clients" figure={`${config.clients.length}`}>
        <ul className="flex flex-col">
          {config.clients.map((c) => (
            <li key={c.id} className="flex items-center gap-3 border-b border-rule py-3 last:border-b-0" style={{ "--c": clientColor(c.id) } as React.CSSProperties}>
              <span className="size-3 shrink-0 rounded-full bg-(--c)" aria-hidden />
              <span className="min-w-0 flex-1 truncate font-medium">{c.name}</span>
              <span className="font-mono text-sm text-muted-foreground tnum">{money.format(c.rate)} / h</span>
            </li>
          ))}
        </ul>
        <p className="text-sm text-muted-foreground text-pretty">Clients, rates, and currency come from hours-ledger.inputs.json in your project.</p>
      </Panel>

      <Panel title="Statements">
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium">Round each entry up to</span>
          <ToggleGroup
            type="single"
            variant="outline"
            value={String(rounding)}
            onValueChange={(v) => v && setRounding(Number(v))}
            className="w-full"
          >
            <ToggleGroupItem value="0" className="h-10 flex-1">Exact</ToggleGroupItem>
            <ToggleGroupItem value="6" className="h-10 flex-1">6 min</ToggleGroupItem>
            <ToggleGroupItem value="15" className="h-10 flex-1">15 min</ToggleGroupItem>
          </ToggleGroup>
          <p className="text-sm text-muted-foreground text-pretty">Entries keep their exact time; rounding applies on the statement, and its foot says so.</p>
        </div>
        <dl className="grid grid-cols-2 gap-3 border-t border-rule pt-4 text-sm">
          <dt className="text-muted-foreground">Weeks start on</dt>
          <dd className="text-right">{config.weekStart === "sun" ? "Sunday" : "Monday"}</dd>
          <dt className="text-muted-foreground">Currency</dt>
          <dd className="text-right font-mono">{config.currency}</dd>
          <dt className="text-muted-foreground">Name on statements</dt>
          <dd className="truncate text-right">{config.name}</dd>
        </dl>
      </Panel>

      <Panel title="Your hours" figure={`${finished.length} entries`}>
        <p className="text-sm text-muted-foreground text-pretty">
          {finished.length ? `Kept in this browser since ${format(first, "MMMM d, yyyy")}.` : "Kept in this browser."} Export moves them anywhere.
        </p>
        <div className="grid grid-cols-2 gap-2">
          <Button variant="outline" className="h-11" onClick={() => exportCsv(ledger.entries, rounding)}>
            <DownloadIcon data-icon="inline-start" />
            Export CSV
          </Button>
          <Button variant="outline" className="h-11" onClick={() => exportJson(ledger.entries, rounding)}>
            <DownloadIcon data-icon="inline-start" />
            Export JSON
          </Button>
          <Button variant="outline" className="col-span-2 h-11" onClick={() => file.current?.click()}>
            <UploadIcon data-icon="inline-start" />
            Import JSON
          </Button>
          <input ref={file} type="file" accept="application/json,.json" className="sr-only" aria-label="Import file" onChange={(e) => onImport(e.target.files?.[0])} />
        </div>
        {message ? (
          <p role="status" className="text-sm">
            {message}
          </p>
        ) : null}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="destructive" className="h-11" disabled={ledger.entries.length === 0}>
              Clear all hours
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Clear every entry?</AlertDialogTitle>
              <AlertDialogDescription>
                This removes {ledger.entries.length} entries from this browser. Export JSON first to keep a copy.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Keep them</AlertDialogCancel>
              <AlertDialogAction variant="destructive" onClick={() => clearEntries()}>
                Clear all hours
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Panel>
    </div>
  )
}
