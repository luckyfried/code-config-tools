import { useRef, useState, type ReactNode } from "react"
import { DownloadIcon, RotateCcwIcon, UploadIcon } from "lucide-react"
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { exportTrip, parseTrip, type TripState } from "@/lib/store"

type SettingsDialogProps = {
  trip: TripState
  packedCount: number
  onImport: (trip: TripState) => void
  onReset: () => void
  children: ReactNode
}

export function SettingsDialog({ trip, packedCount, onImport, onReset, children }: SettingsDialogProps) {
  const [open, setOpen] = useState(false)
  const [status, setStatus] = useState<{ text: string; bad: boolean } | null>(null)
  const file = useRef<HTMLInputElement>(null)

  const importFile = async (f: File) => {
    try {
      const next = parseTrip(JSON.parse(await f.text()))
      if (!next) return setStatus({ text: "That file isn't a Pack List export.", bad: true })
      onImport(next)
      setStatus({ text: `Loaded “${next.name}” with ${next.packed.length} packed.`, bad: false })
    } catch {
      setStatus({ text: "That file isn't a Pack List export.", bad: true })
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o)
        if (!o) setStatus(null)
      }}
    >
      <DialogTrigger asChild>{children}</DialogTrigger>
      <DialogContent className="gap-5 p-5 sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-lg">Settings</DialogTitle>
          <DialogDescription className="text-pretty">
            Your checks live in this browser. Export them to carry this list to another phone or computer.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <Button variant="outline" size="lg" className="justify-start" onClick={() => exportTrip(trip)}>
            <DownloadIcon data-icon="inline-start" />
            Export this list
          </Button>
          <Button variant="outline" size="lg" className="justify-start" onClick={() => file.current?.click()}>
            <UploadIcon data-icon="inline-start" />
            Import a list
          </Button>
          <input
            ref={file}
            type="file"
            accept="application/json,.json"
            className="sr-only"
            tabIndex={-1}
            aria-hidden="true"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void importFile(f)
              e.target.value = ""
            }}
          />
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive" size="lg" className="justify-start" disabled={packedCount === 0}>
                <RotateCcwIcon data-icon="inline-start" />
                Unpack everything for the next trip
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Unpack all {packedCount} items?</AlertDialogTitle>
                <AlertDialogDescription>
                  Every check comes off and the bag empties. The list and anything you added stay.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Keep them</AlertDialogCancel>
                <AlertDialogAction
                  variant="destructive"
                  onClick={() => {
                    onReset()
                    setOpen(false)
                  }}
                >
                  Unpack everything
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
        {status ? (
          <p role="status" className={status.bad ? "text-sm font-medium text-destructive" : "text-sm text-muted-foreground"}>
            {status.text}
          </p>
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
