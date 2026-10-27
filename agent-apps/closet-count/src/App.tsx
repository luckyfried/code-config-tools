import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { CalendarCheck, Layers, Plus, Settings, Shirt, Sparkles, Wind } from "lucide-react"
import { cn } from "@/lib/utils"
import { colorFamily } from "@/lib/color"
import { config, t } from "@/lib/config"
import { longDay, today } from "@/lib/dates"
import { currentSeason, idleDays, isDusty, toggleItemWorn, toggleOutfitWorn, useCloset, wornToday } from "@/lib/store"
import { CATEGORIES, type Item, type Season } from "@/lib/types"
import { useDesktop } from "@/hooks/use-media"
import { Button } from "@/components/ui/button"
import { HueStrip } from "@/components/HueStrip"
import { Closet, type Filters } from "@/components/Closet"
import { Rack, type RackHandle } from "@/components/Rack"
import { WearRow } from "@/components/WearRow"
import { DustyShelf, DustySheet } from "@/components/Dusty"
import { CapsulePanel, CapsuleSheet } from "@/components/Capsule"
import { ItemDialog } from "@/components/ItemDialog"
import { ItemForm } from "@/components/ItemForm"
import { OutfitBuilder } from "@/components/OutfitBuilder"
import { SettingsSheet } from "@/components/SettingsSheet"

type Sheet = "dusty" | "capsule" | "settings" | null

export default function App() {
  const closet = useCloset()
  const desktop = useDesktop()
  const rack = useRef<RackHandle>(null)
  const [filters, setFilters] = useState<Filters>({ season: "all", color: "all" })
  const [picked, setPicked] = useState<string | null>(null)
  const [form, setForm] = useState<{ open: boolean; id?: string }>({ open: false })
  const [builder, setBuilder] = useState<{ open: boolean; id?: string }>({ open: false })
  const [sheet, setSheet] = useState<Sheet>(null)
  const [season, setSeason] = useState<Season>(currentSeason)
  const [focused, setFocused] = useState(0)

  const items = useMemo(
    () => [...closet.items].sort((a, b) => CATEGORIES.indexOf(a.category) - CATEGORIES.indexOf(b.category)),
    [closet.items],
  )
  const byId = useMemo(() => new Map(closet.items.map((i) => [i.id, i])), [closet.items])
  const matches = useCallback(
    (i: Item) => (filters.season === "all" || i.seasons.includes(filters.season)) && (filters.color === "all" || colorFamily(i.color) === filters.color),
    [filters],
  )
  const shown = useMemo(() => items.filter(matches), [items, matches])
  const dusty = useMemo(() => closet.items.filter(isDusty).sort((a, b) => idleDays(b) - idleDays(a)), [closet.items])
  const wornNow = closet.items.filter(wornToday).length
  const outfit = closet.outfits[Math.min(focused, closet.outfits.length - 1)]
  const side = desktop ? "right" : "bottom"
  const anyOpen = !!picked || form.open || builder.open || !!sheet

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (anyOpen || e.metaKey || e.ctrlKey || e.altKey) return
      const el = e.target as HTMLElement
      if (el.closest("input, textarea, select, [role=combobox], [contenteditable=true]")) return
      if (e.key === "ArrowRight") rack.current?.flick(1)
      else if (e.key === "ArrowLeft") rack.current?.flick(-1)
      else if (e.key.toLowerCase() === "w" && outfit) toggleOutfitWorn(outfit.id)
      else return
      e.preventDefault()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [anyOpen, outfit])

  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })

  const today_ = (
    <section id="today" aria-labelledby="today-title" className="flex min-w-0 flex-col gap-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="today-title" className="flex items-baseline gap-2.5 font-display text-2xl font-medium tracking-tight">
          {t("today.title")}
          <span className="font-sans text-sm font-normal text-muted-foreground">{longDay(today())}</span>
        </h2>
        <span className="text-xs text-muted-foreground tabular-nums">{wornNow ? t("today.wornCount", { n: wornNow }) : t("today.nothingYet")}</span>
      </div>
      <Rack
        ref={rack}
        outfits={closet.outfits}
        byId={byId}
        focused={focused}
        onFocus={setFocused}
        onWear={toggleOutfitWorn}
        onEdit={(id) => setBuilder({ open: true, id })}
        onNew={() => setBuilder({ open: true })}
        desktop={desktop}
      />
      <WearRow outfit={outfit} byId={byId} currency={closet.currency} onWear={toggleItemWorn} onPick={setPicked} desktop={desktop} />
    </section>
  )

  const closetView = (
    <Closet items={shown} currency={closet.currency} desktop={desktop} filters={filters} onFilters={setFilters} onPick={setPicked} />
  )
  const dustyView = <DustyShelf items={dusty} onOpen={() => setSheet("dusty")} onPick={setPicked} compact={desktop} />
  const capsuleView = <CapsulePanel closet={closet} season={season} onOpen={() => setSheet("capsule")} />

  return (
    <div className="min-h-dvh">
      <header className={cn("flex items-center justify-between gap-4", desktop ? "px-6 pt-4 pb-3" : "px-4 pt-[max(1rem,env(safe-area-inset-top))] pb-2.5")}>
        <div className="min-w-0">
          <h1 className={cn("truncate font-display font-semibold tracking-tight", desktop ? "text-[2rem] leading-none" : "text-[1.7rem] leading-none")}>
            {config.name}
          </h1>
          <p className="mt-1 text-xs text-muted-foreground tabular-nums">
            {t("summary", { items: closet.items.length, outfits: closet.outfits.length })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {desktop && (
            <>
              <Button variant="outline" className="h-10 px-4" onClick={() => setBuilder({ open: true })}>
                <Layers />
                {t("action.newOutfit")}
              </Button>
              <Button className="h-10 px-4" onClick={() => setForm({ open: true })}>
                <Plus />
                {t("action.addItem")}
              </Button>
            </>
          )}
          <Button variant="ghost" size="icon-lg" className="size-11" onClick={() => setSheet("settings")} aria-label={t("action.settings")}>
            <Settings className="size-5" />
          </Button>
        </div>
      </header>

      <div className={desktop ? "px-6" : "px-4"}>
        <HueStrip items={items} matches={matches} onPick={setPicked} className={desktop ? "h-14" : "h-11"} roomy={desktop} />
      </div>

      {desktop ? (
        <main className="grid grid-cols-[minmax(0,1fr)_minmax(540px,40%)] gap-8 px-6 pt-5 pb-10">
          {closetView}
          <div className="flex min-w-0 flex-col gap-3.5">
            {today_}
            <div className="grid grid-cols-2 gap-3.5">
              {dustyView}
              {capsuleView}
            </div>
          </div>
        </main>
      ) : (
        <main className="flex flex-col gap-7 px-4 pt-4 pb-28">
          {today_}
          {closetView}
          {dustyView}
          {capsuleView}
        </main>
      )}

      {!desktop && (
        <nav className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/92 backdrop-blur-md">
          <div className="grid grid-cols-5">
            {[
              { id: "today", icon: CalendarCheck, label: t("nav.today") },
              { id: "closet", icon: Shirt, label: t("nav.closet") },
              { id: "dusty", icon: Wind, label: t("nav.dusty") },
              { id: "capsule", icon: Sparkles, label: t("nav.capsule") },
            ].map(({ id, icon: Icon, label }) => (
              <button key={id} type="button" onClick={() => scrollTo(id)} className="press flex h-15 flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-muted-foreground">
                <span className="grid size-7 place-items-center">
                  <Icon className="size-5 text-foreground" />
                </span>
                {label}
              </button>
            ))}
            <button type="button" onClick={() => setForm({ open: true })} className="press flex h-15 flex-col items-center justify-center gap-0.5 text-[11px] font-medium">
              <span className="grid size-7 place-items-center rounded-full bg-primary text-primary-foreground">
                <Plus className="size-4" />
              </span>
              {t("nav.add")}
            </button>
          </div>
        </nav>
      )}

      <ItemDialog
        item={picked ? byId.get(picked) : undefined}
        closet={closet}
        season={season}
        onClose={() => setPicked(null)}
        onEdit={(id) => {
          setPicked(null)
          setForm({ open: true, id })
        }}
      />
      <ItemForm
        open={form.open}
        item={form.id ? byId.get(form.id) : undefined}
        onClose={() => setForm({ open: false })}
        onSaved={() => setForm({ open: false })}
      />
      <OutfitBuilder
        open={builder.open}
        outfit={builder.id ? closet.outfits.find((o) => o.id === builder.id) : undefined}
        items={items}
        onClose={() => setBuilder({ open: false })}
        onSaved={(id) => {
          setBuilder({ open: false })
          const n = closet.outfits.findIndex((o) => o.id === id)
          if (n < 0) setTimeout(() => rack.current?.flick(999), 50)
        }}
      />
      <DustySheet open={sheet === "dusty"} onOpenChange={(o) => setSheet(o ? "dusty" : null)} items={dusty} side={side} />
      <CapsuleSheet open={sheet === "capsule"} onOpenChange={(o) => setSheet(o ? "capsule" : null)} closet={closet} season={season} onSeason={setSeason} side={side} />
      <SettingsSheet open={sheet === "settings"} onOpenChange={(o) => setSheet(o ? "settings" : null)} closet={closet} side={side} />
    </div>
  )
}
