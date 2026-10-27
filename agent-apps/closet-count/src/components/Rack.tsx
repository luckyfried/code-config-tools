import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef, type CSSProperties } from "react"
import { Check, Pencil, Plus } from "lucide-react"
import { cn } from "@/lib/utils"
import { config, t } from "@/lib/config"
import { wornToday } from "@/lib/store"
import type { Item, Outfit } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Garment } from "./Garment"

/** Where each slot lies on the flat-lay, as percentages of the card, with its tilt and how far it drifts as the card passes. */
const PLACES: Record<string, { left: number; top: number; w: number; tilt: number; depth: number; z: number }> = {
  layer: { left: 1, top: 4, w: 40, tilt: -7, depth: 34, z: 1 },
  top: { left: 25, top: 0, w: 39, tilt: 3, depth: 18, z: 2 },
  bottom: { left: 52, top: 6, w: 36, tilt: -2, depth: 6, z: 3 },
  shoes: { left: 74, top: 48, w: 24, tilt: 9, depth: -12, z: 4 },
  bag: { left: 77, top: 2, w: 22, tilt: 6, depth: -20, z: 4 },
  accessory: { left: 6, top: 66, w: 18, tilt: -4, depth: 26, z: 5 },
  dress: { left: 25, top: 0, w: 40, tilt: 2, depth: 18, z: 2 },
}
const SPARE = [
  { left: 4, top: 64, w: 20, tilt: 4, depth: 24, z: 5 },
  { left: 78, top: 2, w: 20, tilt: -5, depth: -18, z: 5 },
]

export function FlatLay({ outfit, byId, className }: { outfit: Pick<Outfit, "items">; byId: Map<string, Item>; className?: string }) {
  let spare = 0
  return (
    <div className={cn("relative overflow-hidden rounded-lg bg-flatlay ring-1 ring-flatlay-edge", className)}>
      {config.slots.map((slot) => {
        const id = outfit.items[slot]
        const item = id ? byId.get(id) : undefined
        if (!item) return null
        const place = PLACES[slot] ?? SPARE[spare++ % SPARE.length]
        const wide = slot === "top" && item.category === "dress"
        return (
          <div
            key={slot}
            className="layer-piece absolute aspect-square drop-shadow-[0_6px_8px_rgb(0_0_0/0.16)]"
            style={
              {
                left: `${place.left}%`,
                top: `${place.top}%`,
                width: `${wide ? place.w + 4 : place.w}%`,
                zIndex: place.z,
                "--tilt": `${place.tilt}deg`,
                "--depth": place.depth,
              } as CSSProperties
            }
          >
            <Garment category={item.category} color={item.color} className="size-full" />
          </div>
        )
      })}
    </div>
  )
}

export type RackHandle = { flick: (step: number) => void }

/**
 * The outfit rack: one card per outfit, snapping to center. While a card passes, its layers drift at different rates,
 * set each frame from how far the card sits from center.
 */
export const Rack = forwardRef<
  RackHandle,
  {
    outfits: Outfit[]
    byId: Map<string, Item>
    focused: number
    onFocus: (n: number) => void
    onWear: (id: string) => void
    onEdit: (id: string) => void
    onNew: () => void
    desktop: boolean
  }
>(function Rack({ outfits, byId, focused, onFocus, onWear, onEdit, onNew, desktop }, ref) {
  const scroller = useRef<HTMLDivElement>(null)
  const focusedRef = useRef(focused)
  focusedRef.current = focused

  const cards = () => Array.from(scroller.current?.querySelectorAll<HTMLElement>(".rack-card") ?? [])

  const update = useCallback(() => {
    const el = scroller.current
    if (!el) return
    const mid = el.scrollLeft + el.clientWidth / 2
    let best = 0
    let bestD = Infinity
    cards().forEach((card, n) => {
      const center = card.offsetLeft + card.offsetWidth / 2
      const p = Math.max(-1.5, Math.min(1.5, (center - mid) / card.offsetWidth))
      card.style.setProperty("--p", p.toFixed(3))
      if (Math.abs(p) < bestD) {
        bestD = Math.abs(p)
        best = n
      }
    })
    if (best !== focusedRef.current && best < outfits.length) onFocus(best)
  }, [onFocus, outfits.length])

  const goTo = useCallback((n: number, smooth = true) => {
    const el = scroller.current
    const card = cards()[n]
    if (!el || !card) return
    el.scrollTo({ left: card.offsetLeft + card.offsetWidth / 2 - el.clientWidth / 2, behavior: smooth ? "smooth" : "auto" })
  }, [])

  useImperativeHandle(ref, () => ({
    flick: (step) => goTo(Math.max(0, Math.min(outfits.length - 1, focusedRef.current + step))),
  }), [goTo, outfits.length])

  useEffect(() => {
    const el = scroller.current
    if (!el) return
    let frame = 0
    const onScroll = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(update)
    }
    update()
    el.addEventListener("scroll", onScroll, { passive: true })
    window.addEventListener("resize", onScroll)
    return () => {
      cancelAnimationFrame(frame)
      el.removeEventListener("scroll", onScroll)
      window.removeEventListener("resize", onScroll)
    }
  }, [update])

  /* Once a visit, the rack shows that it moves: it slides to the next outfit and back, unless the person is already using it. */
  useEffect(() => {
    if (outfits.length < 2 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return
    if (sessionStorage.getItem("closet-count.hint")) return
    const el = scroller.current
    const timers = [
      window.setTimeout(() => {
        sessionStorage.setItem("closet-count.hint", "1")
        goTo(1)
      }, 3000),
      window.setTimeout(() => goTo(0), 5200),
    ]
    const stop = () => timers.forEach(clearTimeout)
    el?.addEventListener("pointerdown", stop, { once: true })
    el?.addEventListener("wheel", stop, { once: true })
    return stop
  }, [outfits.length, goTo])

  return (
    <div
      ref={scroller}
      className={cn("rack relative -mx-4 flex snap-x overflow-x-auto px-4 pb-2", desktop ? "gap-4 lg:-mx-1 lg:px-1" : "gap-3")}
      role="list"
      aria-label={t("rack.label")}
      title={desktop ? t("keys.hint") : undefined}
      tabIndex={-1}
    >
      {outfits.map((outfit, n) => {
        const worn = wornToday(outfit)
        return (
          <article
            key={outfit.id}
            role="listitem"
            className={cn(
              "rack-card flex shrink-0 flex-col gap-3 rounded-xl bg-card p-3 shadow-card ring-1 ring-border transition-shadow",
              desktop ? "w-[78%]" : "w-[86%]",
              n === focused && "shadow-lift",
            )}
            data-outfit={outfit.id}
            aria-current={n === focused}
          >
            <FlatLay outfit={outfit} byId={byId} className={desktop ? "aspect-[11/5]" : "aspect-[16/9]"} />
            <div className={cn("flex items-center gap-2", !desktop && "flex-wrap")}>
              <div className="min-w-0 flex-1">
                <h3 className="truncate font-display text-lg leading-tight font-medium">{outfit.name}</h3>
                <p className="text-xs text-muted-foreground tabular-nums">
                  {outfit.wears === 0 ? t("rack.wearsNone") : outfit.wears === 1 ? t("rack.wearsOne") : t("rack.wears", { n: outfit.wears })}
                </p>
              </div>
              <Button variant="ghost" size="icon-lg" className="size-11" onClick={() => onEdit(outfit.id)} aria-label={t("rack.edit")}>
                <Pencil />
              </Button>
              <Button
                variant={worn ? "secondary" : "default"}
                className={cn("h-11 rounded-full px-4", !desktop && "w-full")}
                onClick={() => onWear(outfit.id)}
                aria-pressed={worn}
              >
                {worn && <Check />}
                {worn ? t("rack.worn") : t("rack.markWorn")}
              </Button>
            </div>
          </article>
        )
      })}
      <button
        type="button"
        onClick={onNew}
        className={cn(
          "rack-card press flex shrink-0 flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-border text-muted-foreground transition-colors hover:border-ring hover:text-foreground",
          desktop ? "w-[42%]" : "w-[60%]",
        )}
      >
        <Plus className="size-6" />
        <span className="text-sm font-medium text-foreground">{t("rack.newCard")}</span>
        <span className="text-xs">{t("rack.newCardHint")}</span>
      </button>
    </div>
  )
})
