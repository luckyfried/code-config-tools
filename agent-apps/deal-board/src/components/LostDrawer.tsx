import { RotateCcwIcon } from "lucide-react"
import { CompanyMark } from "@/components/CompanyMark"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { WIDE, useMedia } from "@/hooks/use-media"
import { money, plural, when } from "@/lib/format"
import { LOST, stageBefore, type Deal, type Stage } from "@/lib/pipeline"

/** The Lost drawer: every lost deal, newest first, each one a tap from going back to the stage it was lost at. */
export function LostDrawer({ open, onOpenChange, deals, stages, now, onReopen, onOpenDeal }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  deals: Deal[]
  stages: Stage[]
  now: number
  onReopen: (id: string, to: string) => void
  onOpenDeal: (id: string) => void
}) {
  const wide = useMedia(WIDE)
  const lost = deals.filter((deal) => deal.stage === LOST).sort((a, b) => b.enteredAt - a.enteredAt)
  const total = lost.reduce((sum, deal) => sum + deal.value, 0)
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side={wide ? "right" : "bottom"} className={wide ? "w-full gap-0 sm:max-w-md" : "max-h-[85dvh] gap-0 rounded-t-3xl pb-[env(safe-area-inset-bottom)]"}>
        <SheetHeader className="border-b px-5 pt-5 pb-4">
          <SheetTitle className="text-lg">Lost</SheetTitle>
          <SheetDescription>{lost.length === 0 ? "Nothing lost. Deals you mark lost wait here." : `${plural(lost.length, "deal")}, ${money(total)} in all.`}</SheetDescription>
        </SheetHeader>
        <ul className="flex-1 overflow-y-auto px-3 py-3">
          {lost.map((deal) => {
            const from = stageBefore(deal, stages)
            const fromLabel = stages.find((stage) => stage.id === from)?.label ?? "the first stage"
            return (
              <li key={deal.id} className="flex items-center gap-3 rounded-xl px-2 py-2.5 hover:bg-muted/60">
                <button type="button" onClick={() => onOpenDeal(deal.id)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
                  <CompanyMark company={deal.company} className="size-9" muted />
                  <span className="flex min-w-0 flex-col">
                    <span className="truncate font-medium">{deal.company}</span>
                    <span className="truncate text-[13px] text-muted-foreground">
                      Lost at {fromLabel}, {when(deal.enteredAt, now)}
                    </span>
                  </span>
                  <span className="ml-auto shrink-0 font-medium tabular-nums text-muted-foreground">{money(deal.value)}</span>
                </button>
                <Button variant="outline" size={wide ? "default" : "icon"} onClick={() => onReopen(deal.id, from)} aria-label={`Reopen ${deal.company} in ${fromLabel}`}>
                  <RotateCcwIcon data-icon={wide ? "inline-start" : undefined} />
                  {wide ? "Reopen" : null}
                </Button>
              </li>
            )
          })}
        </ul>
      </SheetContent>
    </Sheet>
  )
}
