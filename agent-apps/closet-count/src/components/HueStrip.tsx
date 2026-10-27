import { useMemo, type CSSProperties } from "react"
import { cn } from "@/lib/utils"
import { hueKey, isHueSorted, toneOf } from "@/lib/color"
import { t } from "@/lib/config"
import { dustLevel } from "@/lib/store"
import type { Item } from "@/lib/types"

/**
 * Every piece as a paint chip, sorted by hue. Each chip starts where its piece sits in the closet below and slides to
 * its place in the color order.
 */
export function HueStrip({
  items,
  matches,
  onPick,
  className,
  roomy = true,
}: {
  items: Item[]
  matches: (item: Item) => boolean
  onPick: (id: string) => void
  className?: string
  roomy?: boolean
}) {
  const keyed = useMemo(
    () => items.map((item) => ({ item, key: hueKey(item.color, dustLevel(item)) })).sort((a, b) => a.key - b.key),
    [items],
  )
  const sorted = keyed.map((k) => k.item)
  const closetIndex = useMemo(() => new Map(items.map((i, n) => [i.id, n])), [items])
  const gap = items.length > 80 ? 1 : items.length > 40 || !roomy ? 2 : 4
  return (
    <nav
      aria-label={t("strip.label")}
      data-hue-sorted={isHueSorted(keyed.map((k) => k.key))}
      className={cn("flex w-full items-stretch", className)}
      style={{ gap, "--gap": `${gap}px` } as CSSProperties}
    >
      {sorted.map((item, n) => {
        const on = matches(item)
        return (
          <button
            key={item.id}
            type="button"
            title={item.name}
            data-tone={toneOf(item.color)}
            aria-label={item.name}
            onClick={() => onPick(item.id)}
            className={cn(
              "chip min-w-0 flex-1 rounded-[3px] outline-offset-2 focus-visible:outline-2 focus-visible:outline-ring",
              !on && "opacity-20",
            )}
            style={
              {
                "--tint": item.color,
                "--i": n,
                "--dx": (closetIndex.get(item.id) ?? n) - n,
                filter: `saturate(calc(var(--swatch-saturate) * ${1 - dustLevel(item) * 0.88}))`,
              } as CSSProperties
            }
          />
        )
      })}
    </nav>
  )
}
