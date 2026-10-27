import { useRef, useState } from "react"
import { Download, Upload } from "lucide-react"
import { cn } from "@/lib/utils"
import { t } from "@/lib/config"
import { shortDay } from "@/lib/dates"
import { exportCloset, importCloset, setCurrency, startOver } from "@/lib/store"
import type { Closet } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
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

const CURRENCIES = ["USD", "EUR", "GBP", "CAD", "AUD", "NZD", "JPY", "CHF", "SEK", "NOK", "DKK", "MXN", "BRL", "INR", "SGD", "HKD", "KRW", "ZAR"]

export function SettingsSheet({ open, onOpenChange, closet, side }: { open: boolean; onOpenChange: (o: boolean) => void; closet: Closet; side: "right" | "bottom" }) {
  const file = useRef<HTMLInputElement>(null)
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null)
  const currencies = CURRENCIES.includes(closet.currency) ? CURRENCIES : [closet.currency, ...CURRENCIES]

  const download = () => {
    const blob = new Blob([exportCloset()], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "closet-count.json"
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const load = async (f: File | undefined) => {
    if (!f) return
    const ok = importCloset(await f.text())
    setNote({ ok, text: ok ? t("settings.importDone") : t("settings.importFailed") })
    if (file.current) file.current.value = ""
  }

  return (
    <Sheet open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) setNote(null) }}>
      <SheetContent side={side} className={cn(side === "bottom" ? "max-h-[88dvh] rounded-t-2xl" : "w-[24rem] sm:max-w-[24rem]")}>
        <SheetHeader className="pr-12">
          <SheetTitle className="font-display text-2xl font-medium">{t("settings.title")}</SheetTitle>
        </SheetHeader>
        <div className="flex flex-col gap-5 overflow-y-auto px-4 pb-6 safe-bottom">
          <label className="flex items-center justify-between gap-3 text-sm font-medium">
            {t("settings.currency")}
            <Select value={closet.currency} onValueChange={setCurrency}>
              <SelectTrigger className="h-10 w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent position="popper" className="max-h-72">
                {currencies.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </label>
          <Separator />
          <div className="flex flex-col gap-2">
            <Button variant="outline" className="h-11 justify-start" onClick={download}>
              <Download />
              {t("settings.export")}
            </Button>
            <p className="text-xs text-muted-foreground">{t("settings.exportHint")}</p>
            <Button variant="outline" className="h-11 justify-start" onClick={() => file.current?.click()}>
              <Upload />
              {t("settings.import")}
            </Button>
            <input ref={file} type="file" accept="application/json,.json" className="hidden" onChange={(e) => load(e.target.files?.[0])} />
            {note && <p className={cn("text-sm", note.ok ? "text-foreground" : "text-destructive")} role="status">{note.text}</p>}
          </div>
          {closet.given.length > 0 && (
            <>
              <Separator />
              <div className="flex flex-col gap-1.5">
                <h3 className="text-sm font-medium">{t("settings.given")}</h3>
                <ul className="text-sm text-muted-foreground">
                  {[...closet.given].reverse().map((g) => (
                    <li key={g.id + g.on} className="flex justify-between gap-3 py-0.5">
                      <span className="truncate">{g.name}</span>
                      <span className="shrink-0 tabular-nums">{shortDay(g.on)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}
          <Separator />
          <div className="flex flex-col gap-2">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="ghost" className="h-11 justify-start text-destructive hover:text-destructive">
                  {t("settings.startOver")}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>{t("settings.startOverConfirm")}</AlertDialogTitle>
                  <AlertDialogDescription>{t("settings.startOverHint")}</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>{t("settings.cancel")}</AlertDialogCancel>
                  <AlertDialogAction variant="destructive" onClick={startOver}>
                    {t("settings.startOver")}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <p className="text-xs text-muted-foreground">{t("settings.startOverHint")}</p>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
