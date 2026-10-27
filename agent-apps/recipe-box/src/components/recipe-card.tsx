import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent } from "react"
import { Bookmark, CalendarPlus, X } from "lucide-react"
import { COPY } from "@/lib/copy"
import { DAY_SHORT, stateWords, type Slot } from "@/lib/box"
import type { Item } from "@/hooks/use-box"
import type { Day } from "@/types"
import { Plates, TimeRing } from "@/components/time-ring"

interface Props {
  item: Item
  index: number
  ratio: number | "failed" | undefined
  onRatio: (v: number | "failed") => void
  live: boolean
  slots: Slot[]
  isOpen: boolean
  setOpen: (id: string | null) => void
  problem?: string
  onChoose: (action: "keep" | "skip" | "week", day?: Day) => void
  onDetail: () => void
  onDragStart: (e: PointerEvent, el: HTMLElement) => void
  firstFreeDay: () => Day
}

const LONG_PRESS_MS = 420

export function RecipeCard(p: Props) {
  const { record, shown, latest } = p.item
  const r = record.body
  const [loaded, setLoaded] = useState(false)
  const [picking, setPicking] = useState(false)
  const ref = useRef<HTMLElement>(null)
  const press = useRef<{ x: number; y: number; touch: boolean; armed: boolean; timer: number; used: boolean } | null>(null)
  const suppressClick = useRef(false)
  const failed = p.ratio === "failed"
  const ratio = typeof p.ratio === "number" ? p.ratio : 0.8
  // Cards arrive two by two, a row at a time, and everything below the first screen arrives with the last row.
  const delay = `${Math.min(Math.floor(p.index / 2), 4) * 110}ms`

  // A held finger may drag the card: once armed, the page stops scrolling under it.
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const stopScroll = (e: TouchEvent) => {
      if (press.current?.armed) e.preventDefault()
    }
    el.addEventListener("touchmove", stopScroll, { passive: false })
    return () => el.removeEventListener("touchmove", stopScroll)
  }, [])

  useEffect(() => {
    if (!p.isOpen) setPicking(false)
  }, [p.isOpen])

  const down = (e: PointerEvent<HTMLElement>) => {
    if (e.button !== 0 || (e.target as HTMLElement).closest("button")) return
    const touch = e.pointerType !== "mouse"
    const state = { x: e.clientX, y: e.clientY, touch, armed: !touch, timer: 0, used: false }
    if (touch) {
      state.timer = window.setTimeout(() => {
        state.armed = true
        state.used = true
        suppressClick.current = true
        p.setOpen(record.id)
        navigator.vibrate?.(8)
      }, LONG_PRESS_MS)
    }
    press.current = state
  }
  const move = (e: PointerEvent<HTMLElement>) => {
    const s = press.current
    if (!s) return
    const far = Math.hypot(e.clientX - s.x, e.clientY - s.y) > (s.touch ? 10 : 6)
    if (!far) return
    if (!s.armed) {
      window.clearTimeout(s.timer)
      press.current = null
      return
    }
    if (p.live && ref.current) {
      suppressClick.current = true
      press.current = null
      p.setOpen(null)
      p.onDragStart(e, ref.current)
    }
  }
  const up = () => {
    if (press.current) window.clearTimeout(press.current.timer)
    press.current = null
  }
  const click = () => {
    if (suppressClick.current) {
      suppressClick.current = false
      return
    }
    p.onDetail()
  }
  const key = (e: KeyboardEvent<HTMLElement>) => {
    if (e.target !== e.currentTarget || e.metaKey || e.ctrlKey || e.altKey) return
    const k = e.key.toLowerCase()
    if (k === "enter") p.onDetail()
    else if (k === "k") p.onChoose("keep")
    else if (k === "s") p.onChoose("skip")
    else if (k === "w") p.onChoose("week", p.firstFreeDay())
    else return
    e.preventDefault()
  }

  const state = latest ? stateWords(latest) : null
  return (
    <article
      ref={ref}
      data-card={record.id}
      data-open={p.isOpen || undefined}
      data-armed={p.isOpen || undefined}
      tabIndex={0}
      aria-label={`${r.title}, ${r.minutes} minutes`}
      aria-keyshortcuts="K S W"
      className="recipe-card cursor-pointer"
      style={{ "--d": delay } as CSSProperties}
      onPointerDown={down}
      onPointerMove={move}
      onPointerUp={up}
      onPointerCancel={up}
      onClick={click}
      onKeyDown={key}
      onContextMenu={(e) => e.preventDefault()}
    >
      <div className="photo" style={{ aspectRatio: String(ratio), background: r.color }}>
        {!failed && (
          <img
            src={r.image}
            alt=""
            draggable={false}
            data-loaded={loaded || undefined}
            decoding="async"
            onLoad={(e) => {
              const img = e.currentTarget
              if (typeof p.ratio !== "number" && img.naturalWidth) p.onRatio(img.naturalWidth / img.naturalHeight)
              // The dish is drawn before its fade starts, so the fade never waits on a decode mid-frame.
              void img.decode().catch(() => undefined).then(() => setLoaded(true))
            }}
            onError={() => p.onRatio("failed")}
          />
        )}
        {failed && (
          <div className="absolute inset-0 grid place-items-center bg-gradient-to-b from-white/10 to-black/25 p-4">
            <span className="text-center font-heading text-2xl leading-tight text-white drop-shadow-[0_1px_2px_rgb(0_0_0/0.4)]">
              {r.title}
            </span>
          </div>
        )}
        {shown.status === "week" && shown.day && (
          <span className="day-badge absolute left-2 top-2 rounded-full bg-foreground px-2 py-0.5 text-[11px] font-semibold text-background shadow-sm">
            {DAY_SHORT[shown.day]}
          </span>
        )}
        <div className="choices" onClick={(e) => e.stopPropagation()}>
          {picking ? (
            <div className="grid grid-cols-7 gap-1" role="group" aria-label="Pick a day">
              {p.slots.map((s) => (
                <button
                  key={s.day}
                  type="button"
                  className="choice px-0 text-[10px]"
                  disabled={!p.live}
                  data-on={(shown.status === "week" && shown.day === s.day) || undefined}
                  onClick={() => {
                    p.onChoose("week", s.day)
                    p.setOpen(null)
                  }}
                >
                  {DAY_SHORT[s.day].slice(0, 2)}
                </button>
              ))}
            </div>
          ) : (
            <div className="flex gap-1.5">
              <button type="button" className="choice" disabled={!p.live} data-on={shown.status === "kept" || undefined}
                onClick={() => { p.onChoose("keep"); p.setOpen(null) }}>
                <Bookmark className="size-4" aria-hidden />
                {COPY.keep}
              </button>
              <button type="button" className="choice" disabled={!p.live}
                onClick={() => { p.onChoose("skip"); p.setOpen(null) }}>
                <X className="size-4" aria-hidden />
                {COPY.skip}
              </button>
              <button type="button" className="choice" disabled={!p.live} data-on={shown.status === "week" || undefined}
                onClick={() => setPicking(true)}>
                <CalendarPlus className="size-4" aria-hidden />
                {COPY.thisWeek}
              </button>
            </div>
          )}
        </div>
      </div>
      {shown.status === "kept" && <span className="ribbon" aria-label="Kept" />}
      <div className="px-3 pb-3 pt-2.5">
        <h3 className="font-heading text-[1.0625rem] leading-snug text-balance">{r.title}</h3>
        <div className="mt-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
          <TimeRing minutes={r.minutes} />
          <span className="tabular-nums">{r.minutes} min</span>
          <span className="mx-0.5 opacity-40">·</span>
          <Plates servings={r.servings} />
        </div>
        {r.why && <p className="mt-1.5 text-[0.8125rem] leading-snug text-muted-foreground text-pretty">{r.why}</p>}
        {state && (
          <p className="mt-2 flex items-start gap-1.5 text-xs leading-4 font-medium" data-state={latest!.status}>
            <span
              className={
                "mt-[5px] size-1.5 shrink-0 rounded-full " +
                (latest!.status === "completed"
                  ? "bg-kept"
                  : latest!.status === "failed"
                    ? "bg-destructive"
                    : latest!.status === "cancelled"
                      ? "bg-muted-foreground"
                      : "status-dot bg-primary")
              }
            />
            <span>{state}</span>
          </p>
        )}
        {p.problem && <p className="mt-1.5 text-xs text-destructive">{p.problem}</p>}
      </div>
    </article>
  )
}
