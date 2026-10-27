import type { CSSProperties } from "react"
import { cn } from "@/lib/utils"
import { t } from "@/lib/config"
import { costPerWear, money } from "@/lib/money"
import { dustLevel, isDusty, wornToday } from "@/lib/store"
import type { Item } from "@/lib/types"
import { Garment } from "./Garment"

/** A piece in the closet: its swatch on a flat-lay card and what it now costs each time it is worn. */
export function ItemTile({
  item,
  currency,
  index,
  onPick,
  showName = false,
}: {
  item: Item
  currency: string
  index: number
  onPick: (id: string) => void
  showName?: boolean
}) {
  const cpw = costPerWear(item)
  const dust = dustLevel(item)
  const today = wornToday(item)
  return (
    <button
      type="button"
      onClick={() => onPick(item.id)}
      title={cpw == null ? item.name : `${item.name}, ${money(cpw, currency)} ${t("cpw.label")}`}
      data-item={item.id}
      data-cpw={cpw ?? ""}
      data-wears={item.wears}
      className="settle press group flex min-w-0 flex-col items-stretch gap-1 text-left outline-none"
      style={{ "--i": index } as CSSProperties}
    >
      <span
        className={cn(
          "relative grid aspect-square place-items-center rounded-md bg-flatlay shadow-card ring-1 ring-flatlay-edge transition-shadow group-hover:shadow-lift group-focus-visible:ring-2 group-focus-visible:ring-ring",
        )}
      >
        <Garment
          category={item.category}
          color={item.color}
          dust={dust}
          className={cn("size-[74%] transition-transform duration-200 group-hover:-translate-y-0.5", isDusty(item) && "dusting")}
        />
        {today && <span className="absolute top-1.5 right-1.5 size-2 rounded-full bg-wear ring-2 ring-flatlay" aria-label={t("item.wornToday")} />}
      </span>
      {showName && <span className="truncate text-[12px] leading-tight font-medium">{item.name}</span>}
      <span className="truncate text-[13px] leading-tight tracking-normal text-muted-foreground tabular-nums">
        {cpw == null ? t("tile.wears", { n: item.wears }) : money(cpw, currency)}
      </span>
    </button>
  )
}
