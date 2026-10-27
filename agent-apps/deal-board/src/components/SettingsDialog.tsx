import { DownloadIcon, RotateCcwIcon, UploadIcon } from "lucide-react"
import { useRef, useState } from "react"
import { toast } from "sonner"
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { config } from "@/config"
import { plural } from "@/lib/format"
import { fromExport, toExport, type Deal } from "@/lib/pipeline"
import { getDeals, setDeals, startOver } from "@/lib/store"

/** Settings: Export the board to a file, Import one back, or start over from the deals the board began with. */
export function SettingsDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const file = useRef<HTMLInputElement>(null)
  const [incoming, setIncoming] = useState<Deal[] | null>(null)
  const [restart, setRestart] = useState(false)
  const [problem, setProblem] = useState("")

  const exportBoard = () => {
    const now = Date.now()
    const data = JSON.stringify(toExport(getDeals(), config.stages, config.currency, now), null, 2)
    const link = document.createElement("a")
    link.href = URL.createObjectURL(new Blob([data], { type: "application/json" }))
    link.download = `deal-board-${new Date(now).toISOString().slice(0, 10)}.json`
    link.click()
    setTimeout(() => URL.revokeObjectURL(link.href), 1000)
    toast.success(`Exported ${plural(getDeals().length, "deal")}.`)
  }

  const read = async (chosen: File | undefined) => {
    if (!chosen) return
    const result = fromExport(await chosen.text(), config.stages, Date.now())
    if (typeof result === "string") setProblem(result)
    else {
      setProblem("")
      setIncoming(result)
    }
    if (file.current) file.current.value = ""
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Settings</DialogTitle>
            <DialogDescription>The board is saved in this browser. Export it to keep a copy, to move it to another browser, or to hand it to your agent for a pipeline summary.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <Button size="lg" onClick={exportBoard} className="justify-start">
              <DownloadIcon data-icon="inline-start" />
              Export the board
            </Button>
            <Button size="lg" variant="outline" onClick={() => file.current?.click()} className="justify-start">
              <UploadIcon data-icon="inline-start" />
              Import a board
            </Button>
            <input ref={file} type="file" accept="application/json,.json" className="sr-only" tabIndex={-1} aria-label="Board file" onChange={(event) => void read(event.target.files?.[0])} />
            {problem ? (
              <p role="alert" className="text-sm text-destructive">
                {problem}
              </p>
            ) : null}
            <Separator className="my-1" />
            <Button size="lg" variant="ghost" onClick={() => setRestart(true)} className="justify-start text-muted-foreground">
              <RotateCcwIcon data-icon="inline-start" />
              Start over with the first deals
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={incoming !== null} onOpenChange={(next) => !next && setIncoming(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Replace the board?</AlertDialogTitle>
            <AlertDialogDescription>
              The file holds {plural(incoming?.length ?? 0, "deal")}. They take the place of the {plural(getDeals().length, "deal")} on the board now.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep this board</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (incoming) setDeals(incoming)
                toast.success(`Imported ${plural(incoming?.length ?? 0, "deal")}.`)
                setIncoming(null)
                onOpenChange(false)
              }}
            >
              Replace the board
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={restart} onOpenChange={setRestart}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Start over?</AlertDialogTitle>
            <AlertDialogDescription>Every move and edit since the board was first filled is cleared, and the first deals come back. Export first to keep a copy.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep this board</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                startOver()
                onOpenChange(false)
              }}
            >
              Start over
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
