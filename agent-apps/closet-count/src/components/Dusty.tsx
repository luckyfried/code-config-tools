import { useState, type CSSProperties } from "react"
import { ArrowRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { config, t } from "@/lib/config"
import { dustLevel, giveAway, idleDays, keepItem } from "@/lib/store"
import type { Item } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
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
import { Garment } from "./Garment"

/** The Dusty shelf: pieces past the Dusty line lean on a shelf, each as faded as its idle weeks. */
export function DustyShelf({ items, onOpen, onPick, compact }: { items: Item[]; onOpen: () => void; onPick: (id: string) => void; compact: boolean }) {
  const shown = items.slice(0, compact ? 6 : 8)
  return (
    <section id="dusty" aria-labelledby="dusty-title" className="flex min-w-0 flex-col gap-2 rounded-xl bg-card p-4 shadow-card ring-1 ring-border">
      <div className="flex items-baseline justify-between gap-2">
        <h2 id="dusty-title" className="font-display text-xl font-medium tracking-tight">
          {t("dusty.title")}
          <span className="ml-2 align-middle text-sm font-normal text-muted-foreground tabular-nums">{items.length}</span>
        </h2>
        <span className="text-xs text-muted-foreground">{t("dusty.lead", { n: config.dustyDays })}</span>
      </div>
      {items.length === 0 ? (
        <p className="py-6 text-sm text-muted-foreground">{t("dusty.none", { n: config.dustyDays })}</p>
      ) : (
        <>
          <div className="relative pt-1">
            <div className="relative z-[1] grid grid-cols-6 items-end gap-1.5 px-1">
              {shown.map((item, n) => (
                <button
                  key={item.id}
                  type="button"
                  title={item.name}
                  onClick={() => onPick(item.id)}
                  className="shelf-in press flex min-w-0 drop-shadow-[0_3px_3px_rgb(0_0_0/0.14)] flex-col items-center gap-1 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  style={{ "--i": n } as CSSProperties}
                >
                  <Garment
                    category={item.category}
                    color={item.color}
                    dust={dustLevel(item)}
                    className="dusting w-full"
                  />
                </button>
              ))}
            </div>
            <div className="h-2 rounded-sm bg-shelf shadow-[0_3px_0_rgb(0_0_0/0.08)]" aria-hidden="true" />
            <div className="mt-1 grid grid-cols-6 gap-1.5 px-1 text-center text-[13px] tracking-normal text-muted-foreground tabular-nums">
              {shown.map((item) => (
                <span key={item.id} className="truncate">{t("dusty.daysShort", { n: idleDays(item) })}</span>
              ))}
            </div>
          </div>
          <Button variant="outline" className="mt-1 h-10 justify-between" onClick={onOpen}>
            {t("dusty.open")}
            <ArrowRight />
          </Button>
        </>
      )}
    </section>
  )
}

export function DustySheet({
  open,
  onOpenChange,
  items,
  side,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  items: Item[]
  side: "right" | "bottom"
}) {
  const [giving, setGiving] = useState<Item | null>(null)
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side={side} className={cn("gap-0", side === "bottom" ? "max-h-[85dvh] rounded-t-2xl" : "w-[26rem] sm:max-w-[26rem]")}>
        <SheetHeader className="pr-12">
          <SheetTitle className="font-display text-2xl font-medium">{t("dusty.title")}</SheetTitle>
          <SheetDescription>{t("dusty.sheetLead")}</SheetDescription>
        </SheetHeader>
        <ul className="flex flex-col gap-1 overflow-y-auto px-4 pb-6 safe-bottom">
          {items.length === 0 && <li className="py-6 text-sm text-muted-foreground">{t("dusty.none", { n: config.dustyDays })}</li>}
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-3 rounded-lg py-2">
              <span className="grid size-14 shrink-0 place-items-center rounded-md bg-flatlay ring-1 ring-flatlay-edge">
                <Garment category={item.category} color={item.color} dust={dustLevel(item)} className="size-[78%]" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium">{item.name}</span>
                <span className="block text-xs text-muted-foreground tabular-nums">{t("dusty.days", { n: idleDays(item) })}</span>
              </span>
              <Button variant="outline" className="h-10" onClick={() => keepItem(item.id)}>
                {t("dusty.keep")}
              </Button>
              <Button variant="ghost" className="h-10 text-destructive hover:text-destructive" onClick={() => setGiving(item)}>
                {t("dusty.give")}
              </Button>
            </li>
          ))}
        </ul>
      </SheetContent>
      <AlertDialog open={!!giving} onOpenChange={(o) => !o && setGiving(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("dusty.confirmTitle", { name: giving?.name ?? "" })}</AlertDialogTitle>
            <AlertDialogDescription>{t("dusty.confirmBody")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("settings.cancel")}</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (giving) giveAway(giving.id)
                setGiving(null)
              }}
            >
              {t("dusty.give")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Sheet>
  )
}
