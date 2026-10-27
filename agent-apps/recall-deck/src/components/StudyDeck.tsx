// The stack and its controls: the top card turns in 3D with a tilt that follows the drag, swipes right for "knew it"
// and left for "again", and the next card rises from the two behind it. Drag values go straight to CSS variables on
// the card, so a drag never re-renders React.

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react"
import { Lightbulb, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cardById, type Card, type CardState } from "@/lib/config"
import { charDiff, isRight, slip } from "@/lib/diff"
import { spanLabel } from "@/lib/dates"
import { graded } from "@/lib/session"
import type { Grade } from "@/lib/sm2"

const GRADES: { g: Grade; label: string }[] = [
  { g: 1, label: "Again" },
  { g: 2, label: "Hard" },
  { g: 3, label: "Good" },
  { g: 4, label: "Easy" },
]

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

interface Props {
  queue: string[]
  state: Record<string, CardState>
  now: string
  typing: boolean
  font: "sans" | "serif"
  demo: boolean
  onGrade: (id: string, grade: Grade) => void
  onLean: (id: string, grade: Grade | null) => void
  onDemoEnd: () => void
  onMore: () => void
  moreLeft: number
  /** Counts every grade and skip, so a card that comes straight back still starts face up. */
  step: number
}

export function StudyDeck(p: Props) {
  const top = p.queue[0]
  const card = top ? cardById.get(top) : undefined
  const [flipped, setFlipped] = useState(false)
  const [typed, setTyped] = useState("")
  const [checked, setChecked] = useState(false)
  const [hint, setHint] = useState(false)
  const dragEl = useRef<HTMLDivElement | null>(null)
  const flipEl = useRef<HTMLDivElement | null>(null)
  const input = useRef<HTMLInputElement | null>(null)
  const m = useRef({ dx: 0, ry: 0, base: 0, lean: null as Grade | null, busy: false })
  const live = useRef(p)
  live.current = p

  const paint = useCallback(() => {
    const d = dragEl.current
    const f = flipEl.current
    if (d) {
      d.style.setProperty("--dx", String(m.current.dx))
      d.style.setProperty("--adx", String(Math.abs(m.current.dx)))
    }
    if (f) f.style.setProperty("--ry", String(m.current.base + m.current.ry))
  }, [])

  const setLive = (on: boolean) => {
    if (on) dragEl.current?.setAttribute("data-live", "")
    else dragEl.current?.removeAttribute("data-live")
  }

  // A new top card starts face up and level; the one behind it rises into place.
  useLayoutEffect(() => {
    m.current = { dx: 0, ry: 0, base: 0, lean: null, busy: false }
    setFlipped(false)
    setTyped("")
    setChecked(false)
    setHint(false)
    dragEl.current?.removeAttribute("data-fly")
    setLive(false)
    paint()
  }, [top, p.step, paint])

  const lean = (g: Grade | null) => {
    const id = live.current.queue[0]
    if (m.current.lean === g || !id) return
    m.current.lean = g
    live.current.onLean(id, g)
  }

  const turn = useCallback(
    (sign = 1) => {
      if (!top) return
      setLive(false)
      m.current.base = sign < 0 ? -180 : 180
      m.current.ry = 0
      paint()
      setFlipped(true)
    },
    [top, paint],
  )

  const check = () => {
    if (!card || flipped) return
    setChecked(typed.trim().length > 0)
    turn(1)
  }

  const fly = useCallback(
    (sign: number, then: () => void) => {
      const d = dragEl.current
      if (!d || m.current.busy) return
      m.current.busy = true
      if (reduced()) {
        then()
        return
      }
      d.removeAttribute("data-live")
      d.setAttribute("data-fly", "")
      m.current.dx = sign * (window.innerWidth * 0.8 + 260)
      paint()
      window.setTimeout(then, 280)
    },
    [paint],
  )

  const grade = useCallback(
    (g: Grade) => {
      if (!top || !flipped || m.current.busy) return
      lean(g)
      const id = top
      fly(g >= 3 ? 1 : -1, () => {
        live.current.onGrade(id, g)
      })
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [top, flipped, fly],
  )

  // Pointer: a tap turns the card; a sideways drag tilts the face up and turns it past 40 degrees, or swipes the
  // answer side off the stack.
  const ptr = useRef({ id: -1, x: 0, y: 0, t: 0, mode: "" as "" | "pending" | "tilt" | "swipe" | "scroll", hx: 0, ht: 0 })
  const onDown = (e: React.PointerEvent) => {
    if (m.current.busy || (e.target as HTMLElement).closest("button,input,a")) return
    ptr.current = { id: e.pointerId, x: e.clientX, y: e.clientY, t: e.timeStamp, mode: "pending", hx: e.clientX, ht: e.timeStamp }
  }
  const onMove = (e: React.PointerEvent) => {
    const s = ptr.current
    if (s.id !== e.pointerId || s.mode === "" || s.mode === "scroll") return
    const dx = e.clientX - s.x
    const dy = e.clientY - s.y
    if (s.mode === "pending") {
      if (Math.abs(dy) > 12 && Math.abs(dy) > Math.abs(dx)) {
        s.mode = "scroll"
        return
      }
      if (Math.abs(dx) < 12) return
      s.mode = flipped ? "swipe" : "tilt"
      dragEl.current?.setPointerCapture(e.pointerId)
      setLive(true)
    }
    if (e.timeStamp - s.ht > 80) {
      s.hx = e.clientX
      s.ht = e.timeStamp
    }
    if (s.mode === "tilt") {
      m.current.ry = Math.max(-80, Math.min(80, dx * 0.32))
    } else {
      m.current.dx = dx
      m.current.ry = Math.max(-8, Math.min(8, dx * 0.03))
      lean(dx > 48 ? 3 : dx < -48 ? 1 : null)
    }
    paint()
  }
  const onUp = (e: React.PointerEvent) => {
    const s = ptr.current
    if (s.id !== e.pointerId) return
    const mode = s.mode
    s.mode = ""
    if (mode === "pending") {
      if (!flipped) {
        if (p.typing && typed.trim()) check()
        else turn(1)
      }
      return
    }
    if (mode !== "tilt" && mode !== "swipe") return
    setLive(false)
    if (mode === "tilt") {
      if (Math.abs(m.current.ry) > 40) turn(m.current.ry)
      else {
        m.current.ry = 0
        paint()
      }
      return
    }
    const v = (e.clientX - s.hx) / Math.max(1, e.timeStamp - s.ht)
    const w = dragEl.current?.offsetWidth ?? 400
    const dx = m.current.dx
    if (Math.abs(dx) > w * 0.28 || (Math.abs(v) > 0.6 && Math.sign(v) === Math.sign(dx))) {
      const g: Grade = dx > 0 ? 3 : 1
      lean(g)
      const id = top!
      fly(Math.sign(dx), () => {
        live.current.onGrade(id, g)
      })
    } else {
      m.current.dx = 0
      m.current.ry = 0
      lean(null)
      paint()
    }
  }

  // Keyboard on a computer: space turns, 1 to 4 grade, the arrows answer again or knew it.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (live.current.demo || e.metaKey || e.ctrlKey || e.altKey) return
      const inField = (e.target as HTMLElement)?.tagName === "INPUT"
      if (inField) return
      if (e.key === " " && !flipped) {
        e.preventDefault()
        turn(1)
      } else if (flipped && ["1", "2", "3", "4"].includes(e.key)) grade(Number(e.key) as Grade)
      else if (flipped && e.key === "ArrowRight") grade(3)
      else if (flipped && e.key === "ArrowLeft") grade(1)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [flipped, grade, turn])

  // The first open walks through the whole promise once, on its own, on a clock from the first frame: a typed slip; a
  // pull on the card's edge that the tilt follows until it turns the rest of the way; the diff; a flick right that
  // grades it Good and carries it off (today's bar shrinks, the bar of its new date grows, today's square fills); the
  // next card rising; a slow pull and its turn; and a long drag left, shadow and rotation following, that sends it back
  // as Again. Any touch, click, or key ends it, and the app puts back the state it started from, so every card stays
  // ungraded.
  useEffect(() => {
    if (!p.demo || !top || reduced()) {
      if (p.demo) live.current.onDemoEnd()
      return
    }
    let stop = false
    const timers: number[] = []
    const t0 = performance.now()
    const wait = (ms: number) => new Promise<void>((r) => timers.push(window.setTimeout(r, ms)))
    const at = (ms: number) => wait(Math.max(0, ms - (performance.now() - t0)))
    const outCubic = (k: number) => 1 - Math.pow(1 - k, 3)
    const inOutCubic = (k: number) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2)
    const inOutSine = (k: number) => (1 - Math.cos(Math.PI * k)) / 2
    const tween = (ms: number, ease: (k: number) => number, apply: (e: number) => void) =>
      new Promise<void>((r) => {
        const start = performance.now()
        const step = (t: number) => {
          if (stop) return r()
          const k = Math.min(1, Math.max(0, (t - start) / ms))
          apply(ease(k))
          paint()
          if (k < 1) requestAnimationFrame(step)
          else r()
        }
        requestAnimationFrame(step)
      })
    const tilt = (to: number, ms: number, ease = outCubic) => {
      const from = m.current.ry
      return tween(ms, ease, (e) => {
        m.current.ry = from + (to - from) * e
      })
    }
    const drag = (to: number, ms: number) => {
      const from = m.current.dx
      return tween(ms, inOutSine, (e) => {
        m.current.dx = from + (to - from) * e
        m.current.ry = Math.max(-8, Math.min(8, m.current.dx * 0.03))
        lean(m.current.dx > 48 ? 3 : m.current.dx < -48 ? 1 : null)
      })
    }
    const end = () => {
      if (stop) return
      stop = true
      timers.forEach(clearTimeout)
      window.removeEventListener("pointerdown", end, true)
      window.removeEventListener("keydown", end, true)
      setLive(false)
      live.current.onDemoEnd()
    }
    window.addEventListener("pointerdown", end, true)
    window.addEventListener("keydown", end, true)
    const run = async () => {
      const first = top
      const answer = cardById.get(first)!.back
      const text = live.current.typing ? slip(answer) : ""
      await at(100)
      for (let i = 1; i <= text.length && !stop; i++) {
        setTyped(text.slice(0, i))
        await wait(22)
      }
      if (stop) return
      if (text) setChecked(true)
      await at(600)
      if (stop) return
      setLive(true)
      await tilt(-62, 400, inOutCubic)
      if (stop) return
      turn(-1)
      await at(2800)
      if (stop) return
      setLive(true)
      const w = dragEl.current?.offsetWidth ?? 400
      await drag(w * 0.6, 1800)
      if (stop) return
      fly(1, () => {
        if (stop) return
        live.current.onGrade(first, 3)
      })
      await at(5400)
      if (stop) return
      const second = live.current.queue[0]
      if (!second) return end()
      setLive(true)
      await tilt(68, 1200, inOutSine)
      if (stop) return
      await at(6600)
      if (stop) return
      turn(1)
      await at(7400)
      if (stop) return
      setLive(true)
      await drag(-w * 0.62, 1400)
      if (stop) return
      fly(-1, () => {
        if (stop) return
        live.current.onGrade(second, 1)
      })
      await at(11200)
      end()
    }
    run()
    return () => {
      stop = true
      timers.forEach(clearTimeout)
      window.removeEventListener("pointerdown", end, true)
      window.removeEventListener("keydown", end, true)
    }
    // The walk-through runs once, from the first card on screen.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [p.demo])

  if (!card) return <Done more={p.moreLeft} onMore={p.onMore} />

  const suggest: Grade | null = checked ? (isRight(typed, card.back) ? 3 : 1) : null
  const stack = p.queue.slice(0, 3)

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 short:contents">
      <div className={`stage relative mx-auto mb-7 min-h-[300px] w-full max-w-[760px] flex-1 sm:aspect-[5/3.1] sm:min-h-0 sm:flex-none short:col-start-1 short:row-span-2 short:row-start-1 short:mb-8 short:aspect-auto lg:aspect-auto lg:min-h-[420px] lg:flex-1 ${p.demo ? "stack-rise" : ""}`}>
        {stack
          .map((id, depth) => ({ id, depth }))
          .reverse()
          .map(({ id, depth }) => {
            const c = cardById.get(id)!
            const isTop = depth === 0
            return (
              <div
                key={id}
                className="slot"
                data-depth={depth}
                data-enter=""
                style={{ "--depth": depth } as React.CSSProperties}
                aria-hidden={!isTop}
              >
                {isTop ? (
                  <div
                    ref={dragEl}
                    className="drag"
                    onPointerDown={onDown}
                    onPointerMove={onMove}
                    onPointerUp={onUp}
                    onPointerCancel={onUp}
                  >
                    <div className="drop" />
                    <div ref={flipEl} className="flip">
                      <Front card={c} font={p.font} hint={hint} onHint={() => setHint(true)} />
                      <Back card={c} font={p.font} typed={checked ? typed : ""} />
                    </div>
                    <span className="stamp stamp-good">Knew it</span>
                    <span className="stamp stamp-again">Again</span>
                  </div>
                ) : (
                  <div className="flip">
                    <Front card={c} font={p.font} hint={false} />
                  </div>
                )}
              </div>
            )
          })}
      </div>

      <div className="mx-auto flex w-full max-w-[760px] flex-col gap-2 short:col-start-2 short:row-start-2 short:self-center">
        {flipped ? (
          <div className="grid grid-cols-4 gap-2">
            {GRADES.map(({ g, label }) => {
              const next = graded(p.state[card.id], g, p.now)
              return (
                <button
                  key={g}
                  type="button"
                  onClick={() => grade(g)}
                  className={`grade grade-${g} flex h-16 flex-col items-center justify-center gap-0.5 rounded-xl text-sm font-semibold outline-none focus-visible:ring-3 focus-visible:ring-ring/50`}
                  data-suggest={suggest === g ? "" : undefined}
                >
                  <span className="flex items-center gap-1.5">
                    <span className="grade-dot hidden size-1.5 rounded-full sm:inline-block" />
                    {label}
                    <kbd className="hidden font-sans text-xs font-semibold opacity-80 lg:inline">{g}</kbd>
                  </span>
                  <span className="tnum text-xs font-medium opacity-80 lg:text-sm">{g === 1 ? "today" : spanLabel(next.interval)}</span>
                </button>
              )
            })}
          </div>
        ) : p.typing ? (
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault()
              check()
            }}
          >
            <Input
              ref={input}
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              placeholder="Type the answer"
              aria-label="Your answer"
              autoComplete="off"
              autoCapitalize="off"
              spellCheck={false}
              className="h-16 flex-1 rounded-xl bg-card px-4 text-lg"
            />
            <Button type="submit" size="lg" className="h-16 rounded-xl px-6 text-base">
              Check
            </Button>
          </form>
        ) : (
          <Button size="lg" className="h-16 rounded-xl text-base" onClick={() => turn(1)}>
            Show answer
            <kbd className="hidden text-xs opacity-60 lg:inline">space</kbd>
          </Button>
        )}
        <p className="hidden text-center text-sm text-muted-foreground lg:block">
          Space turns the card · 1 to 4 grade it · ← again · → knew it · drag the card to tilt or swipe it
        </p>
        <p className="text-center text-xs text-muted-foreground lg:hidden">
          {flipped ? "Swipe right if you knew it, left to see it again" : "Tap the card or drag it sideways to turn it"}
        </p>
      </div>
    </div>
  )
}

function Tags({ card }: { card: Card }) {
  return (
    <div className="flex min-w-0 gap-1.5 overflow-hidden">
      {card.tags.map((t) => (
        <span key={t} className="truncate rounded-full border border-current/20 px-2 py-0.5 font-sans text-[clamp(11px,1.8cqw,14px)] font-medium text-face-soft">
          {t}
        </span>
      ))}
    </div>
  )
}

function Front({ card, font, hint, onHint }: { card: Card; font: string; hint: boolean; onHint?: () => void }) {
  return (
    <div className={`face face-font-${font} flex flex-col`}>
      <div className="flex h-16 items-center justify-between gap-3 px-5">
        <Tags card={card} />
        {card.hint && onHint ? (
          <button
            type="button"
            onClick={onHint}
            className="flex shrink-0 items-center gap-1 rounded-full px-2 py-1 font-sans text-[clamp(12px,1.9cqw,15px)] font-medium text-face-soft hover:bg-current/5"
          >
            <Lightbulb className="size-3.5" /> Hint
          </button>
        ) : null}
      </div>
      <div className="ruled" style={rows(3)}>
        <div className="on-rule" style={span(2)}>
          <p className="text-[clamp(1.75rem,5.5vw,2.375rem)] font-medium text-balance">{card.front}</p>
        </div>
        <div className="on-rule">
          <p className={`font-sans text-[clamp(14px,2.2cqw,17px)] text-face-soft transition-opacity duration-200 ${hint ? "opacity-100" : "opacity-0"}`}>
            {card.hint ?? "\u00a0"}
          </p>
        </div>
      </div>
    </div>
  )
}

function Back({ card, font, typed }: { card: Card; font: string; typed: string }) {
  const diff = typed ? charDiff(typed, card.back) : []
  const right = typed ? isRight(typed, card.back) : false
  const kept = diff.filter((x) => x.kind === "same").reduce((n, x) => n + [...x.text].length, 0)
  // An answer that shares less than half its letters with the right one is shown whole, struck, not as a diff.
  const near = kept * 2 >= [...card.back].length
  const pieces = near ? diff : [{ kind: "extra" as const, text: typed }]
  const off = diff.filter((x) => x.kind !== "same").reduce((n, x) => n + [...x.text].length, 0)
  return (
    <div className={`face face-back face-font-${font} flex flex-col`}>
      <div className="flex h-16 items-center justify-between gap-3 px-5">
        <span className="truncate font-sans text-[clamp(14px,2.4cqw,18px)] font-medium text-face-soft">{card.front}</span>
        <Tags card={card} />
      </div>
      <div className="ruled" style={rows(typed ? 5 : 2)}>
        <div className="on-rule" style={span(2)}>
          <p className="text-[clamp(1.75rem,5.5vw,2.375rem)] font-semibold text-balance">{card.back}</p>
        </div>
        {typed ? (
          <>
            <div className="on-rule" style={span(2)}>
              <p className="text-[clamp(1.125rem,3.6vw,1.5rem)]" aria-label={`You typed ${typed}`}>
                {pieces.map((x, i) => (
                  <span key={i} className={x.kind === "same" ? "" : x.kind === "missing" ? "diff-missing" : "diff-extra"}>
                    {x.text}
                  </span>
                ))}
              </p>
            </div>
            <div className="on-rule">
              <p className={`font-sans text-[clamp(12px,2cqw,15px)] font-semibold tracking-wide uppercase ${right ? "text-right" : "text-warn"}`}>
                {right ? "Right, letter for letter" : near ? `You typed it ${off === 1 ? "one letter" : `${off} letters`} off` : "Not this one"}
              </p>
            </div>
          </>
        ) : null}
      </div>
    </div>
  )
}

/** The ruled body's height in rows, and a line's height in rows: see .ruled and .on-rule. */
const rows = (n: number) => ({ "--rows": n }) as React.CSSProperties
const span = (n: number) => ({ "--span": n }) as React.CSSProperties

function Done({ more, onMore }: { more: number; onMore: () => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="face relative h-40 w-64 rotate-[-3deg]" style={{ position: "relative" }}>
        <div className="flex h-full items-center justify-center pt-10 font-serif text-2xl font-medium">All caught up</div>
      </div>
      <p className="max-w-sm text-sm text-muted-foreground">
        Every card due today is done. The forecast shows when the next ones come back.
      </p>
      {more > 0 ? (
        <Button variant="outline" onClick={onMore}>
          <RotateCcw data-icon="inline-start" /> Learn {Math.min(5, more)} more new cards
        </Button>
      ) : null}
    </div>
  )
}
