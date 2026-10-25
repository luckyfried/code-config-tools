import { useLayoutEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type ReactNode, type RefObject } from "react"
import { useDroppable } from "@dnd-kit/core"
import { SortableContext, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import { Check, ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"
import { LATER, dayOfMonth, weekdayLong, weekdayShort, type DayKey } from "@/lib/dates"
import type { Task } from "@/lib/board"
import { TaskCard } from "./TaskCard"

const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

/** Slides the cards of one list from where they were to where they are after a change (FLIP). */
function useFlip(list: RefObject<HTMLDivElement | null>, key: string, off: boolean) {
  const last = useRef(new Map<string, number>())
  useLayoutEffect(() => {
    const el = list.current
    if (!el) return
    const next = new Map<string, number>()
    const nodes = el.querySelectorAll<HTMLElement>("[data-flip-id]")
    nodes.forEach((n) => next.set(n.dataset.flipId!, n.offsetTop))
    if (!off && !reduceMotion()) {
      nodes.forEach((n) => {
        const was = last.current.get(n.dataset.flipId!)
        const now = next.get(n.dataset.flipId!)!
        if (was !== undefined && was !== now) {
          n.animate([{ transform: `translateY(${was - now}px)` }, { transform: "translateY(0)" }], {
            duration: 260,
            easing: "cubic-bezier(0.23, 1, 0.32, 1)",
          })
        }
      })
    }
    last.current = next
  }, [list, key, off])
}

interface SortableCardProps {
  task: Task
  day: DayKey
  enterClass?: string
  enterDelay?: number
  collapsing: boolean
  onToggle: (id: string) => void
  onOpen: (id: string) => void
  onCardKey: (id: string, e: KeyboardEvent<HTMLButtonElement>) => void
}

function SortableCard({ task, day, enterClass, enterDelay, collapsing, onToggle, onOpen, onCardKey }: SortableCardProps) {
  const { setNodeRef, listeners, attributes, transform, transition, isDragging } = useSortable({
    id: task.id,
    data: { container: day },
  })
  const style: CSSProperties & Record<string, string | undefined> = {
    transform: CSS.Translate.toString(transform),
    transition,
    "--delay": enterDelay ? `${enterDelay}ms` : undefined,
  }
  const { role: _role, tabIndex: _tab, ...a11y } = attributes
  void _role
  void _tab
  return (
    <TaskCard
      ref={setNodeRef}
      task={task}
      style={style}
      data-flip-id={task.id}
      placeholder={isDragging}
      collapsing={collapsing}
      className="touch-manipulation"
      animClass={enterClass}
      onToggle={() => onToggle(task.id)}
      onOpen={() => onOpen(task.id)}
      onCardKey={(e) => onCardKey(task.id, e)}
      {...a11y}
      {...listeners}
    />
  )
}

export interface ColumnProps {
  day: DayKey
  index: number
  isToday: boolean
  isPast: boolean
  open: Task[]
  done: Task[]
  settling: Map<string, "strike" | "collapse">
  entering: Map<string, string>
  firstPaint: boolean
  flipOff: boolean
  /** A past day on a wide screen: a slim rail with a stub per waiting card. */
  rail?: boolean
  onRail?: () => void
  nowMarker?: ReactNode
  todayLabel?: string
  onToggle: (id: string) => void
  onOpen: (id: string) => void
  onCardKey: (id: string, e: KeyboardEvent<HTMLButtonElement>) => void
}

export function Column({
  day, index, isToday, isPast, open, done, settling, entering, firstPaint, flipOff, rail, onRail, nowMarker, todayLabel,
  onToggle, onOpen, onCardKey,
}: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: day, data: { container: day } })
  const list = useRef<HTMLDivElement>(null)
  const [showDone, setShowDone] = useState(true)
  const ids = open.map((t) => t.id)
  useFlip(list, ids.join("|") + "#" + done.length, flipOff)
  const later = day === LATER
  const counted = open.filter((t) => !t.demo).length

  if (rail) {
    return (
      <section
        ref={setNodeRef}
        id={`day-${day}`}
        aria-label={weekdayLong(day)}
        className="wb-day wb-rail relative flex h-full min-w-0 flex-col items-center border-l first:border-l-0"
      >
        <button
          type="button"
          onClick={onRail}
          aria-label={`Show ${weekdayLong(day)}`}
          className="flex w-full flex-1 flex-col items-center gap-3 rounded-lg pt-3 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="flex flex-col items-center">
            <span className="text-xs font-semibold tracking-wide uppercase">{weekdayShort(day)}</span>
            <span className="wb-num text-[1.625rem] leading-tight">{dayOfMonth(day)}</span>
          </span>
          {open.length > 0 ? (
            <span className="flex flex-col items-center gap-1.5">
              {open.map((t) => (
                <span key={t.id} data-stub-id={t.id} className="h-2 w-7 rounded-full bg-muted-foreground/40" />
              ))}
            </span>
          ) : (
            <span className="grid size-7 place-items-center rounded-full border border-dashed border-muted-foreground/40">
              <Check className="size-3.5" aria-hidden />
            </span>
          )}
          {done.length > 0 && <span className="text-xs tabular-nums">{done.length} done</span>}
        </button>
      </section>
    )
  }

  return (
    <section
      ref={setNodeRef}
      id={`day-${day}`}
      aria-label={later ? "Later" : weekdayLong(day)}
      data-today={isToday}
      className={cn(
        "wb-day relative flex h-full w-full shrink-0 flex-col sm:w-1/2 lg:w-auto lg:min-w-0",
        "lg:border-l lg:first:border-l-0",
        isToday && "wb-today lg:rounded-2xl lg:border lg:border-primary/45 lg:first:border-l",
        isToday && "[&+section]:lg:border-l-0",
        later && "bg-muted/35 lg:ml-2 lg:rounded-xl lg:border",
        isOver && !isToday && "bg-accent/40",
      )}
    >
      <header className="flex items-baseline justify-between gap-2 px-4 pt-3 pb-2 lg:px-3">
        <div className={cn("flex min-w-0 items-baseline gap-2", isPast && "opacity-55")}>
          {later ? (
            <h2 className="text-[1.375rem] leading-none font-semibold tracking-tight">Later</h2>
          ) : (
            <>
              <span
                className={cn(
                  "wb-num text-[2rem] leading-none",
                  isToday && "text-[2.75rem] text-primary lg:text-[3.25rem]",
                )}
              >
                {dayOfMonth(day)}
              </span>
              <h2 className={cn("truncate text-sm font-semibold", isToday && "text-base")}>
                {isToday ? (
                  weekdayLong(day)
                ) : (
                  <>
                    <span className="lg:hidden 2xl:inline">{weekdayLong(day)}</span>
                    <span className="hidden lg:inline 2xl:hidden">{weekdayShort(day)}</span>
                  </>
                )}
              </h2>
            </>
          )}
        </div>
        <span className="pb-0.5 text-xs whitespace-nowrap text-muted-foreground tabular-nums">
          {isToday ? (
            <>
              <span className="lg:hidden">Today, </span>
              {todayLabel}
              <span className="hidden lg:inline">{counted ? ` · ${counted} open` : ""}</span>
            </>
          ) : later ? "No day yet" : counted ? `${counted} open` : ""}
        </span>
      </header>

      <div className="relative min-h-0 flex-1">
        <div ref={list} className={cn("wb-scroll absolute inset-0 z-[1] overflow-y-auto overscroll-contain px-3 pt-1 pb-28 lg:px-2 lg:pb-6", isToday && "pl-4 lg:pl-16")}>
          <SortableContext id={day} items={ids} strategy={verticalListSortingStrategy}>
            {open.map((t, row) => (
              <SortableCard
                key={t.id}
                task={t}
                day={day}
                enterClass={entering.get(t.id) ?? (firstPaint ? "wb-enter" : undefined)}
                enterDelay={firstPaint && !entering.has(t.id) ? 60 + index * 45 + row * 35 : undefined}
                collapsing={settling.get(t.id) === "collapse"}
                onToggle={onToggle}
                onOpen={onOpen}
                onCardKey={onCardKey}
              />
            ))}
          </SortableContext>
          {open.length === 0 && (
            <p
              className={cn(
                "rounded-lg border border-dashed px-3 py-5 text-center text-sm text-muted-foreground",
                isOver && "border-primary/60 text-foreground",
              )}
            >
              {later ? "Park things here that have no day yet." : isToday ? "A clear day." : isPast ? "Nothing left here." : "Nothing planned."}
            </p>
          )}
          {done.length > 0 && (
            <div className="mt-3">
              <button
                type="button"
                onClick={() => setShowDone((v) => !v)}
                aria-expanded={showDone}
                className="mb-1 flex h-9 items-center gap-1 rounded-md px-1 text-xs font-medium text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
              >
                <ChevronDown className={cn("size-3.5 transition-transform duration-200", !showDone && "-rotate-90")} aria-hidden />
                {done.length} done
              </button>
              {showDone &&
                done.map((t) => (
                  <TaskCard
                    key={t.id}
                    task={t}
                    compact
                    data-flip-id={t.id}
                    animClass={entering.get(t.id)}
                    onToggle={() => onToggle(t.id)}
                    onOpen={() => onOpen(t.id)}
                    onCardKey={(e) => onCardKey(t.id, e)}
                  />
                ))}
            </div>
          )}
        </div>
        {nowMarker}
      </div>
    </section>
  )
}
