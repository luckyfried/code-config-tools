import { Check, Pencil } from "lucide-react"
import { t } from "@/lib/config"
import { shortDay } from "@/lib/dates"
import { costPerWear, money } from "@/lib/money"
import { capsuleIds, dustLevel, lastWorn, toggleCapsule, toggleItemWorn, wornToday } from "@/lib/store"
import type { Closet, Item, Season } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Garment } from "./Garment"
import { RollingNumber } from "./RollingNumber"
import { WearRing } from "./WearRing"

/** One piece up close: its ring, its cost per wear, and the taps that change them. */
export function ItemDialog({
  item,
  closet,
  season,
  onClose,
  onEdit,
}: {
  item: Item | undefined
  closet: Closet
  season: Season
  onClose: () => void
  onEdit: (id: string) => void
}) {
  return (
    <Dialog open={!!item} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="gap-5 sm:max-w-md">
        {item && <Body item={item} closet={closet} season={season} onEdit={onEdit} />}
      </DialogContent>
    </Dialog>
  )
}

function Body({ item, closet, season, onEdit }: { item: Item; closet: Closet; season: Season; onEdit: (id: string) => void }) {
  const cpw = costPerWear(item)
  const today = wornToday(item)
  const last = lastWorn(item)
  const inCapsule = capsuleIds(closet, season).includes(item.id)
  const seasonName = t(`season.${season}`).toLowerCase()
  return (
    <>
      <DialogHeader className="pr-8">
        <DialogTitle className="font-display text-2xl font-medium">{item.name}</DialogTitle>
        <DialogDescription>
          {[t(`categoryOne.${item.category}`), item.brand, item.seasons.map((s) => t(`season.${s}`)).join(", ")].filter(Boolean).join(" · ")}
        </DialogDescription>
      </DialogHeader>
      <div className="flex items-center gap-5" data-item={item.id} data-cpw={cpw ?? ""} data-wears={item.wears}>
        <WearRing wears={item.wears} className="size-32 shrink-0">
          <Garment category={item.category} color={item.color} dust={dustLevel(item)} className="size-full" />
        </WearRing>
        <dl className="grid flex-1 grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="col-span-2 text-xs text-muted-foreground">{t("item.cpw")}</dt>
          <dd className="col-span-2 -mt-1.5 font-display text-4xl font-semibold tabular-nums">
            {cpw == null ? t("cpw.none") : <RollingNumber value={cpw} from={item.price ?? cpw} format={(v) => money(v, closet.currency)} />}
          </dd>
          <div>
            <dt className="text-xs text-muted-foreground">{t("item.wears")}</dt>
            <dd className="font-medium tabular-nums">{item.wears}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">{t("item.price")}</dt>
            <dd className="font-medium tabular-nums">{item.price == null ? t("cpw.none") : money(item.price, closet.currency)}</dd>
          </div>
          <div className="col-span-2">
            <dt className="text-xs text-muted-foreground">{t("item.lastWorn")}</dt>
            <dd className="font-medium">{last ? shortDay(last) : t("item.never")}</dd>
          </div>
        </dl>
      </div>
      <div className="flex flex-col gap-2">
        <Button className="h-11 rounded-full" variant={today ? "secondary" : "default"} aria-pressed={today} onClick={() => toggleItemWorn(item.id)}>
          {today && <Check />}
          {today ? t("item.wornToday") : t("item.markWorn")}
        </Button>
        <div className="grid grid-cols-[1fr_auto] gap-2">
          <Button variant="outline" className="h-11" aria-pressed={inCapsule} onClick={() => toggleCapsule(season, item.id)}>
            {inCapsule && <Check />}
            {inCapsule ? t("item.inCapsule", { season: seasonName }) : t("item.addCapsule", { season: seasonName })}
          </Button>
          <Button variant="ghost" className="h-11" onClick={() => onEdit(item.id)}>
            <Pencil />
            {t("item.edit")}
          </Button>
        </div>
      </div>
    </>
  )
}
