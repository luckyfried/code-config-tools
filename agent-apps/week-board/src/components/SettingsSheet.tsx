import { useRef, useState, type ChangeEvent, type ReactNode } from "react"
import { Download, Upload } from "lucide-react"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Switch } from "@/components/ui/switch"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { parseBoard, type Board, type Settings } from "@/lib/board"

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  board: Board
  side: "right" | "bottom"
  onSettings: (s: Partial<Settings>) => void
  onImport: (b: Board) => void
  fileStem: string
}

function Row({ label, hint, children }: { label: string; hint: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2.5 border-b py-4 last:border-b-0">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-sm text-muted-foreground">{hint}</p>
      </div>
      {children}
    </div>
  )
}

export function SettingsSheet({ open, onOpenChange, board, side, onSettings, onImport, fileStem }: Props) {
  const file = useRef<HTMLInputElement>(null)
  const [note, setNote] = useState<string | null>(null)
  const s = board.settings

  function exportBoard() {
    const blob = new Blob([JSON.stringify(board, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${fileStem}.json`
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    setNote(`Saved ${board.tasks.length} tasks to ${fileStem}.json.`)
  }

  async function importBoard(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    e.target.value = ""
    if (!f) return
    try {
      const b = parseBoard(JSON.parse(await f.text()))
      if (!b) {
        setNote(`${f.name} is not a Week Board file. Export one from this screen to see the shape.`)
        return
      }
      onImport(b)
      setNote(`Loaded ${b.tasks.length} tasks from ${f.name}.`)
    } catch {
      setNote(`${f.name} could not be read as JSON.`)
    }
  }

  return (
    <Sheet open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) setNote(null) }}>
      <SheetContent
        side={side}
        className={cn("gap-0 bg-background", side === "bottom" ? "max-h-[90dvh] rounded-t-2xl pb-[env(safe-area-inset-bottom)]" : "w-full sm:max-w-md")}
      >
        <SheetHeader>
          <SheetTitle className="text-base">Settings</SheetTitle>
          <SheetDescription>Saved on this device as you change them.</SheetDescription>
        </SheetHeader>
        <div className="overflow-y-auto px-4 pb-4">
          <Row label="Week starts on" hint="The first column of the board.">
            <ToggleGroup
              type="single"
              variant="outline"
              value={s.weekStart}
              onValueChange={(v) => v && onSettings({ weekStart: v as Settings["weekStart"] })}
              className="w-full"
            >
              <ToggleGroupItem value="mon" className="h-11 flex-1">Monday</ToggleGroupItem>
              <ToggleGroupItem value="sun" className="h-11 flex-1">Sunday</ToggleGroupItem>
            </ToggleGroup>
          </Row>
          <Row label="Days on the board" hint="Workdays hides Saturday and Sunday.">
            <ToggleGroup
              type="single"
              variant="outline"
              value={String(s.columns)}
              onValueChange={(v) => v && onSettings({ columns: v === "5" ? 5 : 7 })}
              className="w-full"
            >
              <ToggleGroupItem value="7" className="h-11 flex-1">All seven</ToggleGroupItem>
              <ToggleGroupItem value="5" className="h-11 flex-1">Workdays</ToggleGroupItem>
            </ToggleGroup>
          </Row>
          <Row label="Later rail" hint="A column for things with no day yet.">
            <label className="flex h-11 items-center justify-between gap-3 rounded-lg border bg-card px-3 text-sm">
              Show Later
              <Switch checked={s.later} onCheckedChange={(v) => onSettings({ later: v })} />
            </label>
          </Row>
          <Row label="Your tasks" hint="Export saves every card to a file; import replaces this board with one.">
            <div className="flex gap-2">
              <Button variant="outline" className="h-11 flex-1 gap-2" onClick={exportBoard}>
                <Download className="size-4" aria-hidden />
                Export
              </Button>
              <Button variant="outline" className="h-11 flex-1 gap-2" onClick={() => file.current?.click()}>
                <Upload className="size-4" aria-hidden />
                Import
              </Button>
              <input ref={file} type="file" accept="application/json,.json" className="sr-only" tabIndex={-1} onChange={importBoard} aria-label="Import a board file" />
            </div>
            <p className="min-h-5 text-sm text-muted-foreground" aria-live="polite">{note}</p>
          </Row>
        </div>
      </SheetContent>
    </Sheet>
  )
}
