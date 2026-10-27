// The person's own settings and their progress file: what they set here stays in this browser.

import { useRef, useState } from "react"
import { Download, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { config } from "@/lib/config"
import { clean, STORAGE_KEY, type Saved } from "@/lib/store"

interface Props {
  saved: Saved
  newPerDay: number
  typing: boolean
  onSettings: (s: Partial<Saved["settings"]>) => void
  onImport: (file: Saved) => void
}

export function SettingsView({ saved, newPerDay, typing, onSettings, onImport }: Props) {
  const file = useRef<HTMLInputElement>(null)
  const [note, setNote] = useState("")
  const exportFile = () => {
    const body = JSON.stringify({ deckName: config.deckName, state: saved.state, log: saved.log, settings: saved.settings }, null, 2)
    const a = document.createElement("a")
    a.href = URL.createObjectURL(new Blob([body], { type: "application/json" }))
    a.download = "recall-deck-progress.json"
    a.click()
    URL.revokeObjectURL(a.href)
  }
  const importFile = async (f: File) => {
    try {
      const got = clean(JSON.parse(await f.text()))
      const cards = Object.keys(got.state).length
      const days = Object.keys(got.log).length
      if (!cards && !days) {
        setNote("That file has no cards or days in it. Pick a file Export made.")
        return
      }
      onImport(got)
      setNote(`Brought in ${cards} card${cards === 1 ? "" : "s"} and ${days} day${days === 1 ? "" : "s"}.`)
    } catch {
      setNote("That file is not a progress file. Pick a file Export made.")
    }
  }
  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-4">
      <section className="panel flex flex-col gap-4 rounded-2xl border p-5">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <h2 className="font-semibold">New cards a day</h2>
            <p className="text-sm text-muted-foreground">How many unseen cards each day's session brings in.</p>
          </div>
          <span className="tnum text-2xl font-semibold">{newPerDay}</span>
        </div>
        <Slider min={1} max={30} step={1} value={[newPerDay]} onValueChange={(v) => onSettings({ newPerDay: v[0] })} aria-label="New cards a day" />
      </section>
      <section className="panel flex items-center justify-between gap-4 rounded-2xl border p-5">
        <div>
          <h2 className="font-semibold">Type the answer</h2>
          <p className="text-sm text-muted-foreground">Type before the card turns, and see letter by letter what was off.</p>
        </div>
        <Switch checked={typing} onCheckedChange={(v) => onSettings({ typing: v })} aria-label="Type the answer" />
      </section>
      <section className="panel flex flex-col gap-4 rounded-2xl border p-5">
        <div>
          <h2 className="font-semibold">Your progress</h2>
          <p className="text-sm text-muted-foreground">
            It stays in this browser. Export saves it to a file; Import brings a file back in, here or on another device.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={exportFile}>
            <Download data-icon="inline-start" /> Export
          </Button>
          <Button variant="outline" onClick={() => file.current?.click()}>
            <Upload data-icon="inline-start" /> Import
          </Button>
          <input
            ref={file}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) importFile(f)
              e.target.value = ""
            }}
          />
        </div>
        {note ? <p className="text-sm font-medium" role="status">{note}</p> : null}
        <p className="text-xs text-muted-foreground">Saved in this browser under “{STORAGE_KEY}”.</p>
      </section>
    </div>
  )
}
