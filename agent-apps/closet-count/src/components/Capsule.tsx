import type { CSSProperties } from "react"
import { cn } from "@/lib/utils"
import { config, t } from "@/lib/config"
import { capsuleIds, toggleCapsule } from "@/lib/store"
import { SEASONS, type Closet, type Season } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Garment } from "./Garment"

/** The season's capsule: its pieces as a tight grid under the count, set in the display face. */
export function CapsulePanel({ closet, season, onOpen }: { closet: Closet; season: Season; onOpen: () => void }) {
  const ids = capsuleIds(closet, season)
  const byId = new Map(closet.items.map((i) => [i.id, i]))
  const pieces = ids.map((id) => byId.get(id)!).filter(Boolean)
  return (
    <section id="capsule" aria-labelledby="capsule-title" className="flex min-w-0 flex-col gap-2 rounded-xl bg-card p-4 shadow-card ring-1 ring-border">
      <div className="flex items-baseline justify-between gap-2">
        <h2 id="capsule-title" className="font-display text-xl font-medium tracking-tight">{t("capsule.title")}</h2>
        <Button variant="link" className="h-auto p-0 text-xs" onClick={onOpen}>
          {t("capsule.edit")}
        </Button>
      </div>
      <p className="flex items-baseline gap-2 text-capsule">
        <span className="font-display text-[2.75rem] leading-[0.9] font-semibold tracking-tight tabular-nums" data-capsule-count={pieces.length}>
          {pieces.length}
        </span>
        <span className="text-sm text-muted-foreground">{t("capsule.count", { n: config.capsuleSize, season: t(`season.${season}`).toLowerCase() })}</span>
      </p>
      {pieces.length === 0 ? (
        <p className="py-2 text-sm text-muted-foreground">{t("capsule.empty", { season: t(`season.${season}`).toLowerCase() })}</p>
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(20px,1fr))] gap-1" aria-label={t("capsule.title")}>
          {pieces.map((item, n) => (
            <span
              key={item.id}
              title={item.name}
              className="capsule-cell grid aspect-square place-items-center rounded-[4px] bg-flatlay ring-1 ring-flatlay-edge"
              style={{ "--i": n } as CSSProperties}
            >
              <Garment category={item.category} color={item.color} className="size-[82%]" />
            </span>
          ))}
          {Array.from({ length: Math.max(0, config.capsuleSize - pieces.length) }, (_, n) => (
            <span key={`open-${n}`} className="aspect-square rounded-[4px] border border-dashed border-border" aria-hidden="true" />
          ))}
        </div>
      )}
    </section>
  )
}

export function CapsuleSheet({
  open,
  onOpenChange,
  closet,
  season,
  onSeason,
  side,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  closet: Closet
  season: Season
  onSeason: (s: Season) => void
  side: "right" | "bottom"
}) {
  const chosen = new Set(capsuleIds(closet, season))
  const label = t(`season.${season}`).toLowerCase()
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side={side} className={cn("gap-0", side === "bottom" ? "max-h-[88dvh] rounded-t-2xl" : "w-[30rem] sm:max-w-[30rem]")}>
        <SheetHeader className="pr-12">
          <SheetTitle className="flex items-baseline gap-2 font-display text-2xl font-medium">
            {t("capsule.title")}
            <span className="tabular-nums">{chosen.size}</span>
            <span className="font-sans text-sm font-normal text-muted-foreground">{t("capsule.count", { n: config.capsuleSize, season: label })}</span>
          </SheetTitle>
          <SheetDescription>{t("capsule.sheetLead", { season: label })}</SheetDescription>
        </SheetHeader>
        <div className="px-4 pb-3">
          <ToggleGroup type="single" variant="outline" spacing={0} value={season} onValueChange={(v) => v && onSeason(v as Season)}>
            {SEASONS.map((s) => (
              <ToggleGroupItem key={s} value={s} className="h-10 px-3">
                {t(`season.${s}`)}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
        <div className="grid grid-cols-4 gap-2 overflow-y-auto px-4 pb-6 safe-bottom sm:grid-cols-5">
          {closet.items.map((item) => {
            const on = chosen.has(item.id)
            return (
              <button
                key={item.id}
                type="button"
                aria-pressed={on}
                title={item.name}
                onClick={() => toggleCapsule(season, item.id)}
                className={cn(
                  "press flex flex-col items-center gap-1 rounded-lg p-1.5 ring-1 transition-colors",
                  on ? "bg-accent ring-ring" : "ring-transparent opacity-55 hover:opacity-100",
                )}
              >
                <span className="grid aspect-square w-full place-items-center rounded-md bg-flatlay">
                  <Garment category={item.category} color={item.color} className="size-[76%]" />
                </span>
                <span className="w-full truncate text-center text-[11px]">{item.name}</span>
              </button>
            )
          })}
        </div>
      </SheetContent>
    </Sheet>
  )
}
