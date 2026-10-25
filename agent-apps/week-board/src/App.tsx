import { useCallback, useEffect, useMemo, useReducer, useRef, useState, type CSSProperties, type KeyboardEvent } from "react"
import { flushSync } from "react-dom"
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  closestCenter,
  getFirstCollision,
  pointerWithin,
  rectIntersection,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragOverEvent,
  type DragStartEvent,
  type DropAnimation,
  type PointerSensorProps,
  type UniqueIdentifier,
} from "@dnd-kit/core"
import { CornerDownRight, Plus, Settings2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Column } from "@/components/Column"
import { TaskCard } from "@/components/TaskCard"
import { AddDialog } from "@/components/AddDialog"
import { CardSheet } from "@/components/CardSheet"
import { SettingsSheet } from "@/components/SettingsSheet"
import { cn } from "@/lib/utils"
import { LATER, dayOfMonth, dayProgress, rangeLabel, readToday, weekView, weekdayShort, type DayKey } from "@/lib/dates"
import { carryCandidates, loadBoard, newId, readConfig, saveBoard, seedBoard, type Board, type Task } from "@/lib/board"
import { reduce } from "@/lib/reducer"
import { EASE_MOVE, cardNode, delaySlot, flyIn, ghostOf, reveal, visibleRect, type Ghost } from "@/lib/flight"

/** A mouse drags after 4 px of travel; a finger picks a card up after holding it still for 250 ms. */
class HoldOrDragSensor extends PointerSensor {
  constructor(props: PointerSensorProps) {
    const touch = (props.event as PointerEvent).pointerType === "touch"
    super({
      ...props,
      options: { ...props.options, activationConstraint: touch ? { delay: 250, tolerance: 8 } : { distance: 4 } },
    })
  }
}

const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

function useMedia(query: string): boolean {
  const [hit, setHit] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const m = window.matchMedia(query)
    const on = () => setHit(m.matches)
    m.addEventListener("change", on)
    return () => m.removeEventListener("change", on)
  }, [query])
  return hit
}

const config = readConfig()
const clockAtLoad = readToday()
const storedAtLoad = loadBoard()

function initialBoard(): Board {
  if (storedAtLoad) return storedAtLoad
  return seedBoard(config, weekView(clockAtLoad, config.weekStart, config.columns))
}

/** The opening, in ms after the board appears: the carry-over, then on a board's first open one card shows the
 * drag (lift, travel, a slot opening, the spring drop) and the check (the strike, then the fold). */
const CARRY_AT = 380
const CARRY_STEP = 170
const CARRY_MS = 520
const DEMO = "t-walkthrough"
const DEMO_TITLE = "Hold a card to move it to any day"
const DEMO_IN = 1320
const DEMO_LIFT = 1600
const DEMO_FLY = 1800
const DEMO_FLY_MS = 560
const DEMO_DROP = 2550
const DEMO_CHECK = 2950

const HOURS: [number, string][] = [[9, "9 AM"], [12, "Noon"], [15, "3 PM"], [18, "6 PM"], [21, "9 PM"]]

export default function App() {
  const [board, dispatch] = useReducer(reduce, undefined, initialBoard)
  const { settings, tasks } = board
  const view = useMemo(() => weekView(clockAtLoad, settings.weekStart, settings.columns), [settings.weekStart, settings.columns])
  const columns: DayKey[] = useMemo(() => [...view.days, ...(settings.later ? [LATER] : [])], [view.days, settings.later])
  const desktop = useMedia("(min-width: 1024px)")

  const [now, setNow] = useState(clockAtLoad)
  const [firstPaint, setFirstPaint] = useState(true)
  const [entering, setEntering] = useState(() => new Map<string, string>())
  const [settling, setSettling] = useState(() => new Map<string, "strike" | "collapse">())
  const [activeId, setActiveId] = useState<string | null>(null)
  const [flipHold, setFlipHold] = useState(false)
  const [addOpen, setAddOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)
  const [viewing, setViewing] = useState(0)
  const [shownPast, setShownPast] = useState(() => new Set<DayKey>())
  const tasksNow = useRef(tasks)
  tasksNow.current = tasks
  const days = useRef<HTMLDivElement>(null)
  const dragFrom = useRef<DayKey | null>(null)
  const lastOver = useRef<UniqueIdentifier | null>(null)

  useEffect(() => saveBoard(board), [board])

  const flash = useCallback((id: string, cls: string, ms = 700) => {
    setEntering((m) => new Map(m).set(id, cls))
    window.setTimeout(() => setEntering((m) => {
      const n = new Map(m)
      n.delete(id)
      return n
    }), ms)
  }, [])

  // The live clock for the now marker; it moves a step a minute.
  useEffect(() => {
    const offset = clockAtLoad.getTime() - Date.now()
    const t = window.setInterval(() => setNow(new Date(Date.now() + offset)), 30_000)
    return () => window.clearInterval(t)
  }, [])

  useEffect(() => {
    const t = window.setTimeout(() => setFirstPaint(false), 1400)
    return () => window.clearTimeout(t)
  }, [])

  // Undone cards from past days slide into today one after another, a moment after the board appears.
  // Each card grows out of its day's stub on the rail (or its pill in the day strip) and lands in today, while the
  // count at the top ticks up.
  const carried = useRef(false)
  useEffect(() => {
    if (carried.current) return
    carried.current = true
    const ids = carryCandidates(board, view)
    if (!ids.length) return
    const quick = reducedMotion()
    const timers = ids.map((id, i) =>
      window.setTimeout(() => {
        const from = board.tasks.find((t) => t.id === id)?.day
        const src = quick ? null : visibleRect(`[data-stub-id="${id}"]`, `[data-strip-day="${from}"]`)
        flushSync(() => {
          dispatch({ type: "carry", id, to: view.anchor })
          flash(id, src ? "" : "wb-carry-in", 1600)
        })
        const el = cardNode(id)
        if (el && src) void flyIn(el, src, CARRY_MS)
      }, (quick ? 150 : CARRY_AT) + i * (quick ? 0 : CARRY_STEP)),
    )
    return () => timers.forEach(clearTimeout)
    // The carry runs once, on open, against the board as it was loaded.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // A board's first open: one card shows the drag and the check, then folds away; it is never saved or counted.
  const walked = useRef(false)
  useEffect(() => {
    if (walked.current || storedAtLoad || reducedMotion()) return
    walked.current = true
    const anchor = view.anchor
    const timers: number[] = []
    let ghost: Ghost | null = null
    const at = (ms: number, fn: () => void) => timers.push(window.setTimeout(fn, ms))
    const openIn = (day: DayKey) => tasksNow.current.filter((t) => t.day === day && !t.done)

    at(DEMO_IN, () => {
      dispatch({ type: "add", id: DEMO, title: DEMO_TITLE, day: anchor, before: openIn(anchor)[0]?.id ?? null, demo: true })
      flash(DEMO, "wb-enter", 600)
    })
    at(DEMO_LIFT, () => {
      const el = cardNode(DEMO)
      if (!el) return
      ghost = ghostOf(el)
      ghost.card.classList.add("wb-lifted")
    })
    at(DEMO_FLY, () => {
      const g = ghost
      if (!g) return
      const wide = window.matchMedia("(min-width: 1024px)").matches
      const next = view.days[view.days.indexOf(anchor) + 1]
      const to = wide && next ? next : anchor
      const peers = openIn(to).filter((t) => t.id !== DEMO)
      const before = (to === anchor ? peers[2] : peers[1])?.id ?? null
      flushSync(() => dispatch({ type: "move", id: DEMO, day: to, before, manual: false }))
      delaySlot(to, Math.round(DEMO_FLY_MS * 0.4))
      const el = cardNode(DEMO)
      if (!el) return
      el.getAnimations().forEach((a) => a.cancel())
      el.style.setProperty("visibility", "hidden")
      const r = el.getBoundingClientRect()
      g.root.animate(
        [
          { transform: "translate(0, 0)", width: `${g.rect.width}px` },
          { transform: `translate(${r.left - g.rect.left}px, ${r.top - g.rect.top}px)`, width: `${r.width}px` },
        ],
        { duration: DEMO_FLY_MS, easing: EASE_MOVE, fill: "forwards" },
      )
    })
    at(DEMO_DROP, () => {
      const g = ghost
      if (!g) return
      g.card.classList.replace("wb-lifted", "wb-dropping")
      window.setTimeout(() => {
        g.remove()
        reveal(DEMO)
        ghost = null
      }, 200)
    })
    at(DEMO_CHECK, () => {
      dispatch({ type: "toggle", id: DEMO })
      setSettling((m) => new Map(m).set(DEMO, "strike"))
    })
    at(DEMO_CHECK + 300, () => setSettling((m) => new Map(m).set(DEMO, "collapse")))
    at(DEMO_CHECK + 560, () => {
      setSettling((m) => {
        const n = new Map(m)
        n.delete(DEMO)
        return n
      })
      dispatch({ type: "remove", id: DEMO })
    })

    // The person's first touch or key ends the walkthrough and gives the board back.
    const stop = () => {
      timers.forEach(clearTimeout)
      ghost?.remove()
      ghost = null
      setSettling((m) => {
        const n = new Map(m)
        n.delete(DEMO)
        return n
      })
      dispatch({ type: "remove", id: DEMO })
      off()
    }
    const off = () => {
      window.removeEventListener("pointerdown", stop, true)
      window.removeEventListener("keydown", stop, true)
    }
    window.addEventListener("pointerdown", stop, true)
    window.addEventListener("keydown", stop, true)
    at(DEMO_CHECK + 600, off)
    // The walkthrough runs once, on a board's first open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // A card left on a day the board no longer shows (a settings change) moves to Later, or to today with Later off.
  useEffect(() => {
    for (const t of tasks) {
      if (t.done) continue
      const hidden = t.day === LATER ? !settings.later : !view.days.includes(t.day) && t.day >= view.anchor
      if (hidden) dispatch({ type: "move", id: t.id, day: settings.later ? LATER : view.anchor, manual: false })
    }
  }, [tasks, settings.later, view])

  const byColumn = useMemo(() => {
    const out = new Map<DayKey, { open: Task[]; done: Task[] }>()
    for (const c of columns) out.set(c, { open: [], done: [] })
    for (const t of tasks) {
      const col = out.get(t.day)
      if (!col) continue
      if (!t.done || settling.has(t.id)) col.open.push(t)
      else col.done.push(t)
    }
    for (const c of out.values()) c.done.sort((a, b) => (a.doneAt ?? 0) - (b.doneAt ?? 0))
    return out
  }, [tasks, columns, settling])

  const containerOf = useCallback(
    (id: UniqueIdentifier): DayKey | null => {
      const s = String(id)
      if (columns.includes(s)) return s
      return tasks.find((t) => t.id === s)?.day ?? null
    },
    [columns, tasks],
  )

  // Check: the strike draws, then 300 ms later the card folds away into the column's done list.
  const toggle = useCallback(
    (id: string) => {
      const t = tasks.find((x) => x.id === id)
      if (!t) return
      dispatch({ type: "toggle", id })
      if (t.done) {
        flash(id, "wb-enter", 500)
        return
      }
      const quick = reducedMotion()
      setSettling((m) => new Map(m).set(id, "strike"))
      window.setTimeout(() => setSettling((m) => new Map(m).set(id, "collapse")), quick ? 120 : 300)
      window.setTimeout(() => {
        setSettling((m) => {
          const n = new Map(m)
          n.delete(id)
          return n
        })
        flash(id, "wb-enter", 500)
      }, quick ? 160 : 560)
    },
    [tasks, flash],
  )

  const focusCard = (id: string) =>
    requestAnimationFrame(() => {
      const el = document.querySelector<HTMLElement>(`[data-card-id="${id}"]`)
      el?.focus()
      el?.scrollIntoView({ block: "nearest", inline: "nearest" })
    })

  const onCardKey = useCallback(
    (id: string, e: KeyboardEvent<HTMLButtonElement>) => {
      const t = tasks.find((x) => x.id === id)
      if (!t) return
      const col = columns.indexOf(t.day)
      const list = byColumn.get(t.day)
      const items = list ? [...list.open, ...list.done] : []
      const row = items.findIndex((x) => x.id === id)
      const key = e.key
      if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(key)) {
        if (key === "x" || key === "X") {
          e.preventDefault()
          toggle(id)
        }
        return
      }
      e.preventDefault()
      if (e.shiftKey && !t.done) {
        if (key === "ArrowUp" || key === "ArrowDown") {
          dispatch({ type: "shift", id, by: key === "ArrowUp" ? -1 : 1 })
        } else {
          let c = col + (key === "ArrowLeft" ? -1 : 1)
          while (c >= 0 && c < columns.length && columns[c] !== LATER && columns[c] < view.anchor) c += key === "ArrowLeft" ? -1 : 1
          if (c < 0 || c >= columns.length) return
          dispatch({ type: "move", id, day: columns[c] })
          flash(id, "wb-enter", 500)
        }
        focusCard(id)
        return
      }
      if (key === "ArrowUp" || key === "ArrowDown") {
        const next = items[row + (key === "ArrowUp" ? -1 : 1)]
        if (next) focusCard(next.id)
        return
      }
      for (let c = col + (key === "ArrowLeft" ? -1 : 1); c >= 0 && c < columns.length; c += key === "ArrowLeft" ? -1 : 1) {
        const l = byColumn.get(columns[c])
        const pool = l ? [...l.open, ...l.done] : []
        if (pool.length) {
          focusCard(pool[Math.min(row, pool.length - 1)].id)
          return
        }
      }
    },
    [tasks, columns, byColumn, view.anchor, toggle, flash],
  )

  // N opens Add from anywhere on the board.
  useEffect(() => {
    const on = (e: globalThis.KeyboardEvent) => {
      if (e.key !== "n" && e.key !== "N") return
      if (e.metaKey || e.ctrlKey || e.altKey) return
      const el = e.target as HTMLElement
      if (el.closest("input, textarea, [contenteditable], [role=dialog]")) return
      e.preventDefault()
      setAddOpen(true)
    }
    window.addEventListener("keydown", on)
    return () => window.removeEventListener("keydown", on)
  }, [])

  // While a card is held, a finger's movement drags it instead of scrolling the page.
  const dragging = useRef(false)
  useEffect(() => {
    const stop = (e: TouchEvent) => {
      if (dragging.current) e.preventDefault()
    }
    window.addEventListener("touchmove", stop, { passive: false })
    return () => window.removeEventListener("touchmove", stop)
  }, [])

  // Phone: the day strip follows the swipe, and the board opens on today.
  const scrollToColumn = useCallback((i: number, smooth = true) => {
    const el = days.current
    const target = el?.children[i] as HTMLElement | undefined
    if (!el || !target) return
    el.scrollTo({ left: target.offsetLeft - el.offsetLeft, behavior: smooth && !reducedMotion() ? "smooth" : "auto" })
  }, [])
  useEffect(() => {
    if (desktop) return
    const i = Math.max(0, columns.indexOf(view.anchor))
    scrollToColumn(i, false)
    setViewing(i)
    // Opening position only; later swipes belong to the person.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desktop])
  const onDaysScroll = () => {
    const el = days.current
    if (!el || desktop) return
    const w = (el.children[0] as HTMLElement | undefined)?.offsetWidth || el.clientWidth
    setViewing(Math.min(columns.length - 1, Math.round(el.scrollLeft / w)))
  }

  const sensors = useSensors(useSensor(HoldOrDragSensor))

  const collision: CollisionDetection = useCallback(
    (args) => {
      const within = pointerWithin(args)
      const hits = within.length ? within : rectIntersection(args)
      let overId = getFirstCollision(hits, "id")
      if (overId != null) {
        const key = String(overId)
        if (columns.includes(key)) {
          const ids = new Set((byColumn.get(key)?.open ?? []).map((t) => t.id))
          if (ids.size) {
            const near = closestCenter({
              ...args,
              droppableContainers: args.droppableContainers.filter((c) => ids.has(String(c.id))),
            })
            overId = near[0]?.id ?? overId
          }
        }
        lastOver.current = overId
        return [{ id: overId }]
      }
      return lastOver.current ? [{ id: lastOver.current }] : []
    },
    [columns, byColumn],
  )

  const onDragStart = ({ active }: DragStartEvent) => {
    dragging.current = true
    setActiveId(String(active.id))
    dragFrom.current = containerOf(active.id)
    navigator.vibrate?.(8)
  }

  const onDragOver = ({ active, over }: DragOverEvent) => {
    if (!over) return
    const from = containerOf(active.id)
    const to = containerOf(over.id)
    if (!from || !to || from === to) return
    if (to !== LATER && to < view.anchor) return
    const overIsColumn = columns.includes(String(over.id))
    let before: string | null = null
    if (!overIsColumn) {
      const list = byColumn.get(to)?.open ?? []
      const i = list.findIndex((t) => t.id === over.id)
      const activeRect = active.rect.current.translated
      const below = activeRect && activeRect.top > over.rect.top + over.rect.height / 2
      before = below ? (list[i + 1]?.id ?? null) : String(over.id)
    }
    dispatch({ type: "move", id: String(active.id), day: to, before, manual: false })
  }

  const endDrag = () => {
    dragging.current = false
    setActiveId(null)
    setFlipHold(true)
    requestAnimationFrame(() => requestAnimationFrame(() => setFlipHold(false)))
  }

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    const id = String(active.id)
    const t = tasks.find((x) => x.id === id)
    if (over && t) {
      const to = containerOf(over.id)
      if (to === t.day && over.id !== active.id && !columns.includes(String(over.id))) {
        const list = byColumn.get(to)?.open ?? []
        const from = list.findIndex((x) => x.id === id)
        const at = list.findIndex((x) => x.id === over.id)
        const before = from < at ? (list[at + 1]?.id ?? null) : String(over.id)
        dispatch({ type: "move", id, day: to, before, manual: false })
      }
    }
    if (t && t.carriedFrom && dragFrom.current && dragFrom.current !== t.day) {
      dispatch({ type: "edit", id, carriedFrom: null })
    }
    dragFrom.current = null
    endDrag()
  }

  const dropAnimation: DropAnimation | null = reducedMotion()
    ? null
    : { duration: 180, easing: "cubic-bezier(0.34, 1.4, 0.64, 1)" }

  const activeTask = activeId ? tasks.find((t) => t.id === activeId) ?? null : null
  const openTask = openId ? tasks.find((t) => t.id === openId) ?? null : null
  const carriedCount = tasks.filter((t) => t.day === view.anchor && t.carriedFrom && !t.done).length
  const openCount = tasks.filter((t) => !t.done && !t.demo && columns.includes(t.day)).length
  const progress = dayProgress(now)
  const sheetSide = desktop ? "right" : "bottom"
  const template = columns
    .map((k) =>
      k === LATER ? "minmax(0,0.95fr)" : k < view.anchor && !shownPast.has(k) ? "4.25rem" : k === view.anchor ? "minmax(0,2.1fr)" : "minmax(0,1fr)",
    )
    .join(" ")
  const defaultDay = !desktop && columns[viewing] && (columns[viewing] === LATER || columns[viewing] >= view.anchor) ? columns[viewing] : view.anchor

  return (
    <div className="flex h-dvh flex-col overflow-hidden pt-[env(safe-area-inset-top)] pr-[env(safe-area-inset-right)] pl-[env(safe-area-inset-left)]">
      <header className="mx-auto flex w-full max-w-[1760px] items-center justify-between gap-3 px-4 pt-4 pb-2 lg:px-6 lg:pt-6 lg:pb-4">
        <div className="min-w-0">
          <h1 className="wb-display truncate pb-1 text-[2.125rem] leading-none lg:text-[2.75rem]">{config.name}</h1>
          <p className="mt-1.5 flex min-h-7 flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground lg:text-[0.9375rem]">
            <span className="tabular-nums">{rangeLabel(view.days)}</span>
            <span className="tabular-nums">{openCount} open</span>
            {carriedCount > 0 && (
              <span className="wb-count inline-flex items-center gap-1.5 rounded-full bg-primary px-2.5 py-1 text-xs font-semibold text-primary-foreground">
                <CornerDownRight className="size-3.5" aria-hidden />
                <span className="wb-tick-box">
                  <span key={carriedCount} className="wb-tick">
                    {carriedCount}
                  </span>
                </span>
                carried over
              </span>
            )}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button onClick={() => setAddOpen(true)} className="hidden h-10 gap-2 px-4 lg:inline-flex">
            <Plus className="size-4" aria-hidden />
            Add task
            <kbd className="ml-1 rounded border border-primary-foreground/30 px-1.5 text-xs font-medium opacity-80">N</kbd>
          </Button>
          <Button variant="ghost" size="icon" className="size-11" onClick={() => setSettingsOpen(true)} aria-label="Settings">
            <Settings2 className="size-5" aria-hidden />
          </Button>
        </div>
      </header>

      <nav aria-label="Days" className="flex gap-1 overflow-x-auto px-3 pb-2 lg:hidden">
        {columns.map((k, i) => {
          const active = i === viewing
          const isToday = k === view.today
          const count = byColumn.get(k)?.open.filter((t) => !t.demo).length ?? 0
          return (
            <button
              key={k}
              type="button"
              data-strip-day={k}
              onClick={() => {
                setViewing(i)
                scrollToColumn(i)
              }}
              aria-current={active ? "true" : undefined}
              className={cn(
                "relative flex h-14 min-w-11 flex-1 flex-col items-center justify-center rounded-xl text-xs outline-none transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-ring",
                active ? "bg-primary text-primary-foreground" : isToday ? "text-primary" : "text-muted-foreground",
                !active && k !== LATER && k < view.anchor && "opacity-55",
              )}
            >
              {k === LATER ? (
                <span className="text-sm font-medium">Later</span>
              ) : (
                <>
                  <span className="font-medium">{weekdayShort(k)}</span>
                  <span className="wb-num text-lg leading-tight">{dayOfMonth(k)}</span>
                </>
              )}
              <span
                aria-hidden
                className={cn(
                  "absolute bottom-1.5 size-1 rounded-full bg-current transition-opacity",
                  count && !active ? "opacity-70" : "opacity-0",
                )}
              />
            </button>
          )
        })}
      </nav>

      <DndContext
        sensors={sensors}
        collisionDetection={collision}
        onDragStart={onDragStart}
        onDragOver={onDragOver}
        onDragEnd={onDragEnd}
        onDragCancel={endDrag}
      >
        <main
          ref={days}
          onScroll={onDaysScroll}
          style={{ "--cols": template } as CSSProperties}
          className={cn(
            "wb-days wb-paper mx-auto flex min-h-0 w-full max-w-[1760px] flex-1 touch-pan-x touch-pan-y overflow-x-auto overflow-y-hidden overscroll-x-contain",
            "lg:grid lg:overflow-hidden lg:px-4 lg:pb-4 lg:[grid-template-columns:var(--cols)]",
          )}
        >
          {columns.map((k, i) => {
            const col = byColumn.get(k) ?? { open: [], done: [] }
            const isToday = k === view.today
            return (
              <Column
                key={k}
                day={k}
                index={i}
                isToday={isToday}
                isPast={k !== LATER && k < view.anchor}
                rail={desktop && k !== LATER && k < view.anchor && !shownPast.has(k)}
                onRail={() => setShownPast((s) => new Set(s).add(k))}
                open={col.open}
                done={col.done}
                settling={settling}
                entering={entering}
                firstPaint={firstPaint}
                flipOff={!!activeId || flipHold}
                onToggle={toggle}
                onOpen={setOpenId}
                onCardKey={onCardKey}
                todayLabel={now.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
                nowMarker={
                  isToday ? (
                    <>
                    <div aria-hidden className="pointer-events-none absolute top-1 right-2 bottom-6 left-14 z-0 hidden lg:block">
                      {HOURS.map(([h]) => (
                        <span key={h} className="wb-hour-line absolute inset-x-0 h-px" style={{ "--at": ((h - 6) / 18).toFixed(4) } as CSSProperties} />
                      ))}
                    </div>
                    <div aria-hidden className="pointer-events-none absolute top-1 bottom-6 left-5 z-0 hidden w-10 lg:block">
                      {HOURS.map(([h, label]) => (
                        <span
                          key={h}
                          className="wb-hour absolute left-0 text-xs text-muted-foreground tabular-nums"
                          style={{ "--at": ((h - 6) / 18).toFixed(4) } as CSSProperties}
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                    <div aria-hidden className="pointer-events-none absolute top-1 bottom-6 left-1 z-10 w-[3px] lg:left-3">
                      <span className="absolute inset-0 rounded-full bg-now/15" />
                      <span
                        className="wb-now-fill absolute inset-x-0 top-0 h-full origin-top rounded-full bg-now/55"
                        style={{ "--now-at": progress.toFixed(4) } as CSSProperties}
                      />
                      <span
                        className="wb-now absolute left-1/2 size-[9px] -translate-x-1/2 -translate-y-1/2"
                        style={{ "--now-at": progress.toFixed(4) } as CSSProperties}
                      >
                        <span className="wb-now-dot absolute inset-0 rounded-full bg-now ring-2 ring-background" />
                      </span>
                    </div>
                    </>
                  ) : undefined
                }
              />
            )
          })}
        </main>
        <DragOverlay dropAnimation={dropAnimation}>
          {activeTask ? <TaskCard task={activeTask} lifted className="cursor-grabbing" /> : null}
        </DragOverlay>
      </DndContext>

      <Button
        onClick={() => setAddOpen(true)}
        aria-label="Add a task"
        className="fixed right-[max(1rem,env(safe-area-inset-right))] bottom-[max(1.25rem,env(safe-area-inset-bottom))] z-20 size-14 rounded-full shadow-[0_10px_24px_-8px_var(--shadow)] lg:hidden"
      >
        <Plus className="size-6" aria-hidden />
      </Button>

      <AddDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        view={view}
        laterOn={settings.later}
        defaultDay={defaultDay}
        onAdd={(title, day) => {
          const id = newId()
          dispatch({ type: "add", id, title, day })
          flash(id, "wb-enter", 500)
          if (!desktop) {
            const i = columns.indexOf(day)
            if (i >= 0 && i !== viewing) {
              setViewing(i)
              scrollToColumn(i)
            }
          }
        }}
      />
      <CardSheet
        task={openTask}
        view={view}
        laterOn={settings.later}
        side={sheetSide}
        onClose={() => setOpenId(null)}
        onEdit={(id, change) => dispatch({ type: "edit", id, ...change })}
        onMove={(id, day) => {
          dispatch({ type: "move", id, day })
          flash(id, "wb-enter", 500)
        }}
        onToggle={(id) => {
          toggle(id)
          setOpenId(null)
        }}
        onRemove={(id) => {
          dispatch({ type: "remove", id })
          setOpenId(null)
        }}
      />
      <SettingsSheet
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        board={board}
        side={sheetSide}
        onSettings={(s) => dispatch({ type: "settings", settings: s })}
        onImport={(b) => dispatch({ type: "replace", board: b })}
        fileStem={`week-board-${view.days[0]}`}
      />
    </div>
  )
}
