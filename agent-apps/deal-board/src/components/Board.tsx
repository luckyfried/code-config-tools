import {
  DndContext,
  DragOverlay,
  MouseSensor,
  TouchSensor,
  pointerWithin,
  rectIntersection,
  useDroppable,
  useSensor,
  useSensors,
  type CollisionDetection,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { DealCard, DealFace } from "@/components/DealCard"
import { RollingNumber } from "@/components/RollingNumber"
import { WIDE, useMedia } from "@/hooks/use-media"
import { money, plural, shortMoney } from "@/lib/format"
import { reducedMotion, targetRef, travel } from "@/lib/motion"
import { LOST, WON, stageSummary, type Deal, type Stage } from "@/lib/pipeline"
import { cn } from "@/lib/utils"

export interface BoardProps {
  deals: Deal[]
  stages: Stage[]
  now: number
  won: { count: number; value: number }
  onOpen: (id: string) => void
  onMove: (id: string, to: string, from: DOMRect) => void
  onOpenLost: () => void
  onOpenWon: () => void
  onDragStarted: () => void
  /** A short screen: the page scrolls, and the columns keep a usable height below the headline. */
  short?: boolean
}

const collide: CollisionDetection = (args) => {
  const within = pointerWithin(args)
  return within.length > 0 ? within : rectIntersection(args)
}

let reveal: (stage: string, smooth?: boolean) => Promise<void> = async () => {}
/** Brings a stage's column into view on a phone, where one stage fills the screen; on a wide screen every column is in view already. */
export const revealStage = (stage: string, smooth = true) => reveal(stage, smooth)

export function Board(props: BoardProps) {
  const { deals, stages, now, onMove, onDragStarted } = props
  const wide = useMedia(WIDE)
  const [activeId, setActiveId] = useState<string | null>(null)
  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 320, tolerance: 8 } }),
  )
  const byStage = useMemo(() => {
    const map = new Map<string, Deal[]>(stages.map((stage) => [stage.id, []]))
    for (const deal of deals) map.get(deal.stage)?.push(deal)
    for (const list of map.values()) list.sort((a, b) => b.value - a.value || a.company.localeCompare(b.company))
    return map
  }, [deals, stages])
  const active = activeId ? deals.find((deal) => deal.id === activeId) : undefined
  const justDragged = useRef(0)

  const onDragStart = (event: DragStartEvent) => {
    setActiveId(String(event.active.id))
    onDragStarted()
    if (event.activatorEvent.type.startsWith("touch")) navigator.vibrate?.(12)
  }
  const onDragEnd = (event: DragEndEvent) => {
    const id = String(event.active.id)
    setActiveId(null)
    justDragged.current = performance.now()
    const rect = event.active.rect.current.translated
    const from = rect ? new DOMRect(rect.left, rect.top, rect.width, rect.height) : undefined
    const to = event.over?.data.current?.stage as string | undefined
    const deal = deals.find((d) => d.id === id)
    if (deal && from && to && to !== deal.stage) onMove(id, to, from)
    else requestAnimationFrame(() => void travel(id, from))
  }
  const open = useCallback(
    (id: string) => {
      if (performance.now() - justDragged.current > 250) props.onOpen(id)
    },
    [props],
  )

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={collide}
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragCancel={() => setActiveId(null)}
      autoScroll={wide ? true : { threshold: { x: 0, y: 0.18 } }}
      accessibility={{
        screenReaderInstructions: { draggable: "To move a deal, open it and pick its stage, or press and hold it, then drag it to another stage." },
      }}
    >
      {wide ? (
        <WideBoard {...props} byStage={byStage} activeId={activeId} open={open} />
      ) : (
        <CompactBoard {...props} byStage={byStage} activeId={activeId} open={open} dragging={activeId !== null} />
      )}
      <DragOverlay dropAnimation={null}>{active ? <DealFace deal={active} now={now} lifted /> : null}</DragOverlay>
    </DndContext>
  )
}

interface LayoutProps extends BoardProps {
  byStage: Map<string, Deal[]>
  activeId: string | null
  open: (id: string) => void
}

function WideBoard({ stages, byStage, now, activeId, open, won, deals, onOpenLost, onOpenWon }: LayoutProps) {
  const lost = deals.filter((deal) => deal.stage === LOST).length
  return (
    <div className="flex min-h-0 flex-1 gap-3 px-6 pb-5">
      <div className="grid min-h-0 flex-1 auto-cols-[minmax(13.5rem,1fr)] grid-flow-col gap-3 overflow-x-auto overscroll-x-contain">
        {stages.map((stage) => (
          <StageColumn key={stage.id} stage={stage} deals={byStage.get(stage.id) ?? []} now={now} activeId={activeId} open={open} />
        ))}
      </div>
      <div className="flex w-[8.5rem] shrink-0 flex-col gap-3">
        <CloseTile kind={WON} count={won.count} value={won.value} label="Won" detail="last 90 days" onClick={onOpenWon} dragging={activeId !== null} />
        <CloseTile kind={LOST} count={lost} label="Lost" detail="Open the drawer" onClick={onOpenLost} dragging={activeId !== null} />
      </div>
    </div>
  )
}

function StageColumn({ stage, deals, now, activeId, open, className }: { stage: Stage; deals: Deal[]; now: number; activeId: string | null; open: (id: string) => void; className?: string }) {
  const { setNodeRef, isOver } = useDroppable({ id: `stage:${stage.id}`, data: { stage: stage.id } })
  const summary = stageSummary(deals, stage)
  return (
    <section
      ref={setNodeRef}
      data-stage=""
      data-stage-id={stage.id}
      style={{ "--stage-raw": stage.color } as React.CSSProperties}
      aria-label={`${stage.label}, ${plural(summary.count, "deal")}`}
      className={cn(
        "stage-column relative flex min-h-0 flex-col rounded-[18px] border border-column-border transition-[background-color,box-shadow] duration-150",
        isOver && "ring-2 ring-stage/60",
        className,
      )}
    >
      <header className="flex flex-col gap-1.5 px-3.5 pt-3.5 pb-3">
        <div className="flex items-center gap-2">
          <span className="size-2.5 shrink-0 rounded-full bg-stage shadow-[0_0_0_3px_color-mix(in_oklab,var(--stage)_22%,transparent)]" />
          <h3 className="truncate text-[15px] font-semibold tracking-[-0.01em]">{stage.label}</h3>
          <span className="stage-pill rounded-full px-1.5 py-px text-xs font-semibold tabular-nums">{stage.probability}%</span>
          <span className="ml-auto text-[13px] font-medium text-muted-foreground tabular-nums">{summary.count}</span>
        </div>
        <div className="flex items-baseline gap-1.5" data-subtotal={summary.weighted}>
          <RollingNumber value={summary.weighted} format={money} className="text-xl font-semibold tracking-[-0.02em] text-headline" />
          <span className="truncate text-xs text-muted-foreground">of {shortMoney(summary.value)}</span>
        </div>
      </header>
      <div data-lane="" className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto overscroll-y-contain px-2 pb-2">
        {deals.map((deal) => (
          <DealCard key={deal.id} deal={deal} now={now} onOpen={open} dimmed={deal.id === activeId} />
        ))}
        {deals.length === 0 ? (
          <p className="m-1 grid flex-1 place-items-center rounded-xl border border-dashed border-stage/35 px-3 py-8 text-center text-[13px] text-muted-foreground">
            {activeId ? `Drop here for ${stage.label}` : `No deals in ${stage.label} yet`}
          </p>
        ) : null}
      </div>
    </section>
  )
}

function CloseTile({ kind, count, value, label, detail, onClick, dragging }: { kind: string; count: number; value?: number; label: string; detail: string; onClick: () => void; dragging: boolean }) {
  const { setNodeRef, isOver } = useDroppable({ id: `stage:${kind}`, data: { stage: kind } })
  const register = targetRef(kind)
  return (
    <button
      type="button"
      ref={(el) => {
        setNodeRef(el)
        return register(el)
      }}
      onClick={onClick}
      className={cn(
        "flex flex-1 flex-col items-start gap-1 rounded-[18px] border p-3.5 text-left transition-[background-color,border-color,box-shadow] duration-150",
        kind === WON ? "close-won border-won/30" : "border-dashed border-column-border bg-column hover:bg-muted/60",
        dragging && "border-solid",
        isOver && (kind === WON ? "ring-2 ring-won/60" : "bg-lost/15 ring-2 ring-lost/70"),
      )}
    >
      <span className={cn("mb-1 size-2.5 rounded-full", kind === WON ? "bg-won shadow-[0_0_0_3px_color-mix(in_oklab,var(--won)_22%,transparent)]" : "bg-lost")} />
      <span className="text-[15px] font-semibold">{label}</span>
      <span className="text-2xl font-semibold tabular-nums tracking-[-0.02em]">{value !== undefined ? shortMoney(value) : count}</span>
      <span className="text-[13px] leading-snug text-muted-foreground">
        {value !== undefined ? (
          <>
            <span className="whitespace-nowrap">{plural(count, "deal")},</span> <span className="whitespace-nowrap">{detail}</span>
          </>
        ) : (
          detail
        )}
      </span>
      <span className="mt-auto text-xs text-muted-foreground">{dragging ? `Drop to mark ${label.toLowerCase()}` : ""}</span>
    </button>
  )
}

function CompactBoard({ stages, byStage, now, activeId, open, deals, onOpenLost, onOpenWon, dragging, short }: LayoutProps & { dragging: boolean }) {
  const scroller = useRef<HTMLDivElement>(null)
  const [index, setIndex] = useState(0)
  const lost = deals.filter((deal) => deal.stage === LOST).length

  const show = useCallback(
    (stage: string, smooth = true) =>
      new Promise<void>((done) => {
        const el = scroller.current
        const i = stages.findIndex((s) => s.id === stage)
        const column = el?.children[i] as HTMLElement | undefined
        if (!el || !column) return done()
        const left = column.offsetLeft - el.offsetLeft
        const inView = left >= el.scrollLeft - 2 && left + column.offsetWidth <= el.scrollLeft + el.clientWidth + 2
        if (inView) return done()
        const instant = !smooth || reducedMotion()
        el.scrollTo({ left, behavior: instant ? "instant" : "smooth" })
        if (instant) return done()
        const finish = () => {
          el.removeEventListener("scrollend", finish)
          clearTimeout(timer)
          done()
        }
        const timer = setTimeout(finish, 700)
        el.addEventListener("scrollend", finish)
      }),
    [stages],
  )

  useEffect(() => {
    reveal = show
    return () => {
      reveal = async () => {}
    }
  }, [show])

  const chips = useRef<HTMLElement>(null)
  useEffect(() => {
    // The row starts at a whole chip, as far right as keeps the current chip in view with the side padding past it.
    const nav = chips.current
    const items = nav ? (Array.from(nav.children) as HTMLElement[]) : []
    const chip = items[index]
    if (!nav || !chip) return
    const pad = parseFloat(getComputedStyle(nav).paddingLeft)
    const need = chip.offsetLeft + chip.offsetWidth + pad - nav.clientWidth
    const first = items.find((item) => item.offsetLeft - pad >= need) ?? chip
    const left = Math.max(0, Math.min(first.offsetLeft - pad, nav.scrollWidth - nav.clientWidth))
    nav.scrollTo({ left, behavior: reducedMotion() ? "instant" : "smooth" })
  }, [index])

  const onScroll = () => {
    const el = scroller.current
    const first = el?.children[0] as HTMLElement | undefined
    if (!el || !first) return
    setIndex(Math.round(el.scrollLeft / first.offsetWidth))
  }

  return (
    <div className={cn("flex flex-col", short ? "h-[92dvh] shrink-0" : "min-h-0 flex-1")}>
      <nav ref={chips} aria-label="Stages" className="snap-x-board chip-row relative flex shrink-0 scroll-px-4 gap-2 overflow-x-auto px-4 pt-1 pb-3">
        {stages.map((stage, i) => (
          <StageChip
            key={stage.id}
            id={stage.id}
            color={stage.color}
            label={stage.label}
            count={byStage.get(stage.id)?.length ?? 0}
            current={i === index}
            dragging={dragging}
            onClick={() => void show(stage.id)}
          />
        ))}
        <StageChip id={WON} label="Won" count={null} current={false} dragging={dragging} onClick={onOpenWon} />
        <StageChip id={LOST} label="Lost" count={lost} current={false} dragging={dragging} onClick={onOpenLost} target />
      </nav>
      <div ref={scroller} onScroll={onScroll} className="snap-x-board flex min-h-0 flex-1 overflow-x-auto">
        {stages.map((stage) => (
          <div key={stage.id} className="flex min-h-0 w-full shrink-0 snap-start flex-col px-4 pb-3 sm:w-1/2 sm:pr-2 sm:last:pr-4">
            <StageColumn stage={stage} deals={byStage.get(stage.id) ?? []} now={now} activeId={activeId} open={open} />
          </div>
        ))}
      </div>
    </div>
  )
}

function StageChip({ id, color, label, count, current, dragging, onClick, target }: { id: string; color?: string; label: string; count: number | null; current: boolean; dragging: boolean; onClick: () => void; target?: boolean }) {
  const { setNodeRef, isOver } = useDroppable({ id: `chip:${id}`, data: { stage: id } })
  const register = targetRef(id)
  return (
    <button
      type="button"
      ref={(el) => {
        setNodeRef(el)
        return target ? register(el) : undefined
      }}
      onClick={onClick}
      aria-current={current ? "true" : undefined}
      data-stage=""
      style={color ? ({ "--stage-raw": color } as React.CSSProperties) : undefined}
      className={cn(
        "flex h-11 shrink-0 snap-start items-center gap-2 rounded-full border px-4 text-[15px] font-medium transition-[background-color,border-color,color,box-shadow] duration-150",
        current ? "border-foreground/15 bg-foreground text-background" : "border-column-border bg-card text-foreground",
        dragging && "border-dashed",
        isOver && "ring-3 ring-stage/60",
        isOver && id === WON && "ring-won/70",
        isOver && id === LOST && "ring-lost/80",
      )}
    >
      <span className={cn("size-2 rounded-full", id === WON ? "bg-won" : id === LOST ? "bg-lost" : "bg-stage")} />
      {label}
      {count !== null ? <span className={cn("tabular-nums", current ? "text-background/70" : "text-muted-foreground")}>{count}</span> : null}
    </button>
  )
}
