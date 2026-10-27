import { Check } from "lucide-react"
import { cn } from "@/lib/utils"
import { config, t } from "@/lib/config"
import { costPerWear, money } from "@/lib/money"
import { wornToday } from "@/lib/store"
import type { Item, Outfit } from "@/lib/types"
import { Garment } from "./Garment"
import { RollingNumber } from "./RollingNumber"
import { WearRing } from "./WearRing"

/**
 * The pieces of the outfit in front of the rack, each in its thirty-wears ring with its cost per wear. A tap marks the
 * one piece worn today, and the number rolls down to its new cost.
 */
export function WearRow({
  outfit,
  byId,
  currency,
  onWear,
  onPick,
  desktop,
}: {
  outfit: Outfit | undefined
  byId: Map<string, Item>
  currency: string
  onWear: (id: string) => void
  onPick: (id: string) => void
  desktop: boolean
}) {
  const pieces = outfit
    ? config.slots.map((s) => outfit.items[s]).filter((id): id is string => !!id).map((id) => byId.get(id)).filter((i): i is Item => !!i)
    : []
  return (
    <div className="grid grid-cols-4 gap-1.5">
      {pieces.map((item, n) => {
        const cpw = costPerWear(item)
        const today = wornToday(item)
        return (
          <div
            key={`${outfit!.id}-${item.id}`}
            className={cn("flex min-w-0 flex-col items-center gap-1.5 rounded-xl px-1 py-1 text-center")}
            data-item={item.id}
            data-cpw={cpw ?? ""}
            data-wears={item.wears}
          >
            <button type="button" onClick={() => onPick(item.id)} className="press rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label={item.name}>
              <WearRing wears={item.wears} className={desktop ? "size-16" : "size-[68px]"}>
                <Garment category={item.category} color={item.color} className="size-full" />
              </WearRing>
            </button>
            <div className="flex flex-col items-center leading-tight">
              {cpw == null ? (
                <span className="text-base font-semibold tabular-nums">{t("cpw.none")}</span>
              ) : (
                <RollingNumber
                  className="text-base font-semibold"
                  value={cpw}
                  from={item.price ?? cpw}
                  delay={250 + n * 90}
                  format={(v) => money(v, currency)}
                />
              )}
              <span className="text-[13px] tracking-normal text-muted-foreground tabular-nums">
                {item.wears >= 30 ? t("tile.wears", { n: item.wears }) : t("ring.of", { n: item.wears })}
              </span>
            </div>
            <button
              type="button"
              onClick={() => onWear(item.id)}
              aria-pressed={today}
              className={cn(
                desktop ? "h-8" : "h-10",
                "press inline-flex items-center gap-1 rounded-full px-3 text-xs font-medium ring-1 transition-colors",
                today ? "bg-primary text-primary-foreground ring-primary" : "ring-border hover:bg-muted",
              )}
            >
              {today && <Check className="size-3.5" />}
              {today ? t("ring.wornToday") : t("ring.markToday")}
            </button>
          </div>
        )
      })}
    </div>
  )
}
