import { useRef, useState } from "react"
import { format } from "date-fns"
import { Download, Upload } from "lucide-react"
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
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import type { Macros } from "@/lib/config"
import { readSaved, type Saved } from "@/lib/store"

type Props = {
  saved: Saved
  targets: Macros
  startTargets: Macros
  onTargets: (t: Macros | undefined) => void
  onReplace: (s: Saved) => void
}

const KEYS: { key: keyof Macros; label: string; unit: string }[] = [
  { key: "calories", label: "Calories", unit: "kcal" },
  { key: "protein", label: "Protein", unit: "g" },
  { key: "carbs", label: "Carbs", unit: "g" },
  { key: "fat", label: "Fat", unit: "g" },
]

export function SettingsPanel({ saved, targets, startTargets, onTargets, onReplace }: Props) {
  const [draft, setDraft] = useState(() => Object.fromEntries(KEYS.map((k) => [k.key, String(targets[k.key])])) as Record<keyof Macros, string>)
  const [note, setNote] = useState("")
  const [incoming, setIncoming] = useState<{ data: Saved; name: string } | null>(null)
  const file = useRef<HTMLInputElement>(null)

  const parsed = Object.fromEntries(KEYS.map((k) => [k.key, Number(draft[k.key].replace(",", "."))])) as Macros
  const valid = KEYS.every((k) => parsed[k.key] > 0)
  const custom = saved.targets !== undefined

  const saveTargets = (e: React.FormEvent) => {
    e.preventDefault()
    if (!valid) return
    onTargets(parsed)
    setNote("Targets saved.")
  }

  const exportLog = () => {
    const body = JSON.stringify({ app: "plate-log", exported: new Date().toISOString(), ...saved }, null, 2)
    const url = URL.createObjectURL(new Blob([body], { type: "application/json" }))
    const a = document.createElement("a")
    a.href = url
    a.download = `plate-log-${format(new Date(), "yyyy-MM-dd")}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const pickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    e.target.value = ""
    if (!f) return
    try {
      const data = readSaved(JSON.parse(await f.text()))
      if (!data) throw new Error("shape")
      setIncoming({ data, name: f.name })
    } catch {
      setNote(`${f.name} is not a Plate Log export.`)
    }
  }

  const days = incoming ? Object.keys(incoming.data.days).length : 0

  return (
    <div className="flex flex-col gap-6">
      <form onSubmit={saveTargets} className="flex flex-col gap-4" aria-labelledby="targets">
        <h3 id="targets" className="text-lg font-semibold">
          Daily targets
        </h3>
        <FieldGroup className="grid grid-cols-2 gap-4">
          {KEYS.map((k) => (
            <Field key={k.key} data-invalid={!(parsed[k.key] > 0) ? true : undefined}>
              <FieldLabel htmlFor={`t-${k.key}`}>
                {k.label} <span className="font-normal text-muted-foreground">{k.unit}</span>
              </FieldLabel>
              <Input
                id={`t-${k.key}`}
                inputMode="decimal"
                className="h-11 text-base tabular-nums"
                value={draft[k.key]}
                aria-invalid={!(parsed[k.key] > 0) ? true : undefined}
                onChange={(e) => {
                  setDraft({ ...draft, [k.key]: e.target.value })
                  setNote("")
                }}
              />
            </Field>
          ))}
        </FieldGroup>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" className="h-11" disabled={!valid}>
            Save targets
          </Button>
          {custom && (
            <Button
              type="button"
              variant="ghost"
              className="h-11"
              onClick={() => {
                onTargets(undefined)
                setDraft(Object.fromEntries(KEYS.map((k) => [k.key, String(startTargets[k.key])])) as Record<keyof Macros, string>)
                setNote("Back to the starting targets.")
              }}
            >
              Use the starting targets
            </Button>
          )}
        </div>
      </form>

      <Separator />

      <section aria-labelledby="your-log" className="flex flex-col gap-3">
        <h3 id="your-log" className="text-lg font-semibold">
          Your log
        </h3>
        <p className="text-sm text-pretty text-muted-foreground">
          The log stays in this browser. Export it to keep a copy or to open it on another device.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" className="h-11" onClick={exportLog}>
            <Download data-icon="inline-start" />
            Export
          </Button>
          <Button variant="outline" className="h-11" onClick={() => file.current?.click()}>
            <Upload data-icon="inline-start" />
            Import
          </Button>
          <input ref={file} type="file" accept="application/json,.json" className="sr-only" tabIndex={-1} aria-hidden="true" onChange={pickFile} />
        </div>
      </section>

      <p role="status" aria-live="polite" className="min-h-5 text-sm text-muted-foreground">
        {note}
      </p>

      <AlertDialog open={incoming !== null} onOpenChange={(o) => !o && setIncoming(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Replace this log?</AlertDialogTitle>
            <AlertDialogDescription>
              {incoming?.name} holds {days} {days === 1 ? "day" : "days"} and {incoming?.data.foods.length ?? 0} of your own foods. It
              takes the place of everything logged in this browser.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep this log</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (incoming) onReplace(incoming.data)
                setNote(`Imported ${incoming?.name}.`)
                setIncoming(null)
              }}
            >
              Replace
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
