import { useCallback, useEffect, useMemo, useRef, useState, type PointerEvent } from "react"
import { RecipeCard } from "@/components/recipe-card"
import { RecipeSheet } from "@/components/recipe-sheet"
import { Receipt } from "@/components/receipt"
import { WeekStrip } from "@/components/week-strip"
import { useBox, type Item } from "@/hooks/use-box"
import { lastChecked, newestList, weekSlots, whenWords } from "@/lib/box"
import { COPY, type CopyKey } from "@/lib/copy"
import { EASE_OUT, reduced } from "@/lib/motion"
import type { Filter } from "@/lib/store"
import type { AppConfig, Day, Status } from "@/types"

const FILTERS: { id: Filter; label: CopyKey; has: (s: Status) => boolean }[] = [
  { id: "box", label: "filterBox", has: (s) => s !== "skipped" },
  { id: "new", label: "filterNew", has: (s) => s === "new" },
  { id: "kept", label: "filterKept", has: (s) => s === "kept" },
  { id: "week", label: "filterWeek", has: (s) => s === "week" },
  { id: "skipped", label: "filterSkipped", has: (s) => s === "skipped" },
]

function useWide() {
  const query = "(min-width: 768px)"
  const [wide, setWide] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const m = window.matchMedia(query)
    const on = () => setWide(m.matches)
    m.addEventListener("change", on)
    return () => m.removeEventListener("change", on)
  }, [])
  return wide
}

export default function App({ config }: { config: AppConfig }) {
  const box = useBox(config)
  const wide = useWide()
  const live = box.mode === "live"
  const slots = useMemo(() => weekSlots(config.week_start), [config.week_start])
  const [openCard, setOpenCard] = useState<string | null>(null)
  const [detail, setDetail] = useState<string | null>(null)
  const detailItem = box.items.find((x) => x.record.id === detail) ?? null
  // Tags carried by two or more recipes become filters of their own, the most used first.
  const tags = useMemo(() => {
    const n = new Map<string, number>()
    for (const x of box.items) for (const t of x.record.body.tags) n.set(t, (n.get(t) ?? 0) + 1)
    return [...n].filter(([, c]) => c > 1).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 6)
  }, [box.items])
  const tag = box.filter.startsWith("tag:") ? box.filter.slice(4) : null
  const filter = (tag ? null : FILTERS.find((f) => f.id === box.filter)) ?? FILTERS[0]
  const shown = tag
    ? box.items.filter((x) => x.record.body.tags.includes(tag) && x.shown.status !== "skipped")
    : box.items.filter((x) => filter.has(x.shown.status))
  const list = newestList(box.lists)
  const checked = lastChecked(box.events)
  const itemsRef = useRef<Item[]>(box.items)
  useEffect(() => {
    itemsRef.current = box.items
  }, [box.items])

  // A long-pressed card closes when the person touches anywhere else.
  useEffect(() => {
    if (!openCard) return
    const away = (e: Event) => {
      if (!(e.target as HTMLElement).closest(`[data-card="${CSS.escape(openCard)}"]`)) setOpenCard(null)
    }
    document.addEventListener("pointerdown", away)
    return () => document.removeEventListener("pointerdown", away)
  }, [openCard])

  const firstFreeDay = useCallback((): Day => {
    const taken = new Set(itemsRef.current.filter((x) => x.shown.status === "week").map((x) => x.shown.day))
    const fromToday = slots.slice(Math.max(0, slots.findIndex((s) => s.today)))
    return (fromToday.find((s) => !taken.has(s.day)) ?? slots.find((s) => !taken.has(s.day)) ?? slots[0]).day
  }, [slots])

  // A card dragged onto a day slot is a week choice for that day.
  const startDrag = useCallback(
    (item: Item, e: PointerEvent, el: HTMLElement) => {
      const size = wide ? 112 : 96
      const ghost = document.createElement("div")
      ghost.className = "drag-ghost"
      ghost.style.cssText = `left:0;top:0;width:${size}px;height:${size}px;background:${item.record.body.color}`
      const img = document.createElement("img")
      img.src = item.record.body.image
      img.alt = ""
      img.style.cssText = "width:100%;height:100%;object-fit:cover;display:block"
      ghost.append(img)
      document.body.append(ghost)
      el.style.opacity = "0.45"
      let hover: HTMLElement | null = null
      const place = (x: number, y: number) => {
        ghost.style.transform = `translate(${x - size / 2}px, ${y - size / 2}px) rotate(4deg)`
        const slot = (document.elementFromPoint(x, y) as HTMLElement | null)?.closest<HTMLElement>("[data-slot]") ?? null
        if (slot !== hover) {
          hover?.removeAttribute("data-target")
          slot?.setAttribute("data-target", "")
          hover = slot
        }
      }
      place(e.clientX, e.clientY)
      const move = (ev: globalThis.PointerEvent) => place(ev.clientX, ev.clientY)
      const end = async () => {
        window.removeEventListener("pointermove", move)
        window.removeEventListener("pointerup", end)
        window.removeEventListener("pointercancel", end)
        el.style.opacity = ""
        const day = hover?.dataset.slot as Day | undefined
        hover?.removeAttribute("data-target")
        const to = (day ? hover!.querySelector("[data-slot-target]") : el.querySelector(".photo"))!.getBoundingClientRect()
        if (!reduced()) {
          const from = ghost.getBoundingClientRect()
          await ghost
            .animate(
              [
                { transform: ghost.style.transform, width: `${from.width}px`, height: `${from.height}px` },
                {
                  transform: `translate(${to.left}px, ${to.top}px)`,
                  width: `${to.width}px`,
                  height: `${to.height}px`,
                  borderRadius: day ? "50%" : "14px",
                  opacity: day ? 1 : 0,
                },
              ],
              { duration: 320, easing: EASE_OUT, fill: "forwards" },
            )
            .finished.catch(() => undefined)
        }
        ghost.remove()
        if (day) void box.choose(item.record, "week", day, true)
      }
      window.addEventListener("pointermove", move)
      window.addEventListener("pointerup", end)
      window.addEventListener("pointercancel", end)
    },
    [wide, box],
  )

  const titles = useMemo(
    () => Object.fromEntries(box.items.map((x) => [x.record.id, { title: x.record.body.title, day: x.shown.day }])),
    [box.items],
  )
  const count = (f: (typeof FILTERS)[number]) => box.items.filter((x) => f.has(x.shown.status)).length
  const owner = config.name?.trim() ? COPY.title.replace("{name}", config.name.trim()) : COPY.titleNoName

  return (
    <div className="paper relative min-h-dvh">
      <header className="relative z-10 px-3 pt-4 md:px-8 md:pt-7">
        <div className="flex flex-col gap-1 md:flex-row md:items-end md:justify-between md:gap-8">
          <div className="min-w-0">
            <h1 className="font-heading text-[1.75rem] leading-none tracking-tight md:text-[2.75rem]">{owner}</h1>
            {config.ask && <p className="mt-1.5 text-[0.8125rem] leading-snug text-balance text-muted-foreground md:text-base">{config.ask}</p>}
          </div>
          <p className="flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground md:text-sm">
            <span className={"size-1.5 rounded-full " + (box.glow ? "status-dot bg-primary" : checked ? "bg-kept" : "bg-muted-foreground/50")} />
            {box.mode === "sample"
              ? COPY.sampleWeek
              : box.glow
                ? COPY.agentMaking
                : checked
                  ? `${COPY.agentChecked} ${whenWords(checked)}`
                  : COPY.agentAsk}
          </p>
        </div>
        <nav className="-mx-3 mt-3 flex gap-1.5 overflow-x-auto px-3 pb-1 [scrollbar-width:none] md:mx-0 md:mt-5 md:px-0" aria-label="Show">
          {FILTERS.map((f) => {
            const on = !tag && f.id === filter.id
            return (
              <button
                key={f.id}
                type="button"
                aria-pressed={on}
                onClick={() => box.setFilter(f.id)}
                className={
                  "flex h-8 shrink-0 items-center gap-1.5 rounded-full border px-3 text-[0.8125rem] font-semibold transition-colors " +
                  (on ? "border-transparent bg-[var(--chip-on)] text-[var(--chip-on-foreground)]" : "bg-[var(--chip)] text-foreground hover:bg-muted")
                }
              >
                {COPY[f.label]}
                <span className={"tabular-nums " + (on ? "opacity-70" : "text-muted-foreground")}>{box.ready ? count(f) : ""}</span>
              </button>
            )
          })}
          {tags.length > 0 && <span className="mx-1 w-px shrink-0 self-stretch bg-border" aria-hidden />}
          {tags.map(([t]) => {
            const on = tag === t
            return (
              <button
                key={t}
                type="button"
                aria-pressed={on}
                onClick={() => box.setFilter(on ? "box" : `tag:${t}`)}
                className={
                  "flex h-8 shrink-0 items-center rounded-full border border-dashed px-3 text-[0.8125rem] font-medium transition-colors " +
                  (on ? "border-transparent bg-[var(--chip-on)] text-[var(--chip-on-foreground)]" : "text-muted-foreground hover:bg-muted hover:text-foreground")
                }
              >
                {t}
              </button>
            )
          })}
        </nav>
      </header>
      <main className="relative z-10 px-3 pb-[calc(var(--strip-h)+env(safe-area-inset-bottom)+1.25rem)] pt-3 md:px-8 md:pt-4">
        {box.ready && shown.length > 0 && (
          <div className="masonry">
            {shown.map((item, n) => (
              <RecipeCard
                key={item.record.id}
                item={item}
                index={n}
                ratio={box.ratios[item.record.body.image]}
                onRatio={(v) => box.setRatio(item.record.body.image, v)}
                live={live}
                slots={slots}
                isOpen={openCard === item.record.id}
                setOpen={setOpenCard}
                problem={box.problem[item.record.id]}
                onChoose={(action, day) => void box.choose(item.record, action, day)}
                onDetail={() => setDetail(item.record.id)}
                onDragStart={(e, el) => startDrag(item, e, el)}
                firstFreeDay={firstFreeDay}
              />
            ))}
          </div>
        )}
        {box.ready && shown.length === 0 && (
          <div className="mx-auto max-w-sm py-20 text-center">
            <p className="font-heading text-2xl">
              {box.items.length ? COPY.emptyFilter : COPY.emptyBox}
            </p>
            <p className="mt-2 text-sm text-muted-foreground">
              {box.items.length
                ? COPY.emptyFilterHint
                : COPY.emptyBoxHint}
            </p>
          </div>
        )}
      </main>
      <WeekStrip
        slots={slots}
        items={box.items}
        glow={box.glow}
        live={live}
        list={list}
        note={box.stripNote}
        onPlan={() => void box.planWeek()}
        onList={() => list && box.openReceipt(box.receiptList ? null : list.id)}
        onRecipe={(item) => setDetail(item.record.id)}
      />
      {box.receiptList && (
        <Receipt
          key={box.receiptList.id + box.receiptList.revision}
          list={box.receiptList}
          name={config.name}
          household={config.household}
          titles={titles}
          ticked={box.ticked}
          onTick={(line) => box.toggleTick(box.receiptList!.id, line)}
          onClose={() => box.openReceipt(null)}
        />
      )}
      <RecipeSheet
        item={detailItem}
        wide={wide}
        live={live}
        household={config.household}
        slots={slots}
        events={box.events}
        onClose={() => setDetail(null)}
        onChoose={(action, day) => detailItem && void box.choose(detailItem.record, action, day)}
      />
    </div>
  )
}
