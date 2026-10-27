// Recall Deck: today's cards, the deck, the forecast, and the settings, on one page. The session state lives here;
// every change the person makes is written to this browser at once, so a reload shows the same deck.

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ChartColumn, Layers, List, Settings2 } from "lucide-react"
import { BrowseView } from "@/components/BrowseView"
import { ForecastChart, ForecastKey } from "@/components/ForecastChart"
import { ForecastView } from "@/components/ForecastView"
import { HeatRow, HeatWeeks } from "@/components/HeatStrip"
import { SettingsView } from "@/components/SettingsView"
import { StudyDeck } from "@/components/StudyDeck"
import { Totals } from "@/components/Totals"
import { config } from "@/lib/config"
import { today } from "@/lib/dates"
import { buildQueue, forecast, graded, totals } from "@/lib/session"
import { comesBackToday, type Grade } from "@/lib/sm2"
import { initial, merge, readSaved, writeSaved, type Saved } from "@/lib/store"

type View = "study" | "browse" | "forecast" | "settings"
const VIEWS: { id: View; label: string; icon: typeof Layers }[] = [
  { id: "study", label: "Study", icon: Layers },
  { id: "browse", label: "Browse", icon: List },
  { id: "forecast", label: "Forecast", icon: ChartColumn },
  { id: "settings", label: "Settings", icon: Settings2 },
]
const fromHash = (): View => {
  const v = window.location.hash.replace(/^#\/?/, "")
  return VIEWS.some((x) => x.id === v) ? (v as View) : "study"
}

const stored = readSaved()

export default function App() {
  const now = useMemo(() => today(), [])
  // The first-open walk-through plays on a copy: it grades a card for real on screen, writes nothing, and puts this
  // starting state back when it ends.
  const [start] = useState(() => {
    const s = initial(stored)
    return { saved: s, queue: buildQueue(s, now, s.settings.newPerDay ?? config.newPerDay) }
  })
  const demoOn = useRef(stored === null && config.cards.length > 0)
  const [saved, setSaved] = useState<Saved>(start.saved)
  const newPerDay = saved.settings.newPerDay ?? config.newPerDay
  const typing = saved.settings.typing ?? config.typing
  const [extra, setExtra] = useState(0)
  const [queue, setQueue] = useState(start.queue)
  const [step, setStep] = useState(0)
  const [lean, setLean] = useState<{ id: string; g: Grade } | null>(null)
  const [demo, setDemo] = useState(stored === null && config.cards.length > 0)
  const [view, setView] = useState<View>(fromHash)

  useEffect(() => {
    const on = () => setView(fromHash())
    window.addEventListener("hashchange", on)
    return () => window.removeEventListener("hashchange", on)
  }, [])
  useEffect(() => {
    document.title = `${config.deckName} · Recall Deck`
  }, [])

  const keep = useCallback((next: Saved) => {
    if (!demoOn.current) writeSaved(next)
    return next
  }, [])

  const onGrade = useCallback(
    (id: string, g: Grade) => {
      const again = comesBackToday(g)
      setSaved((s) => {
        const prev = s.state[id]
        const next = graded(prev, g, now)
        const l = s.log[now] ?? { seen: 0, fresh: 0, again: 0 }
        return keep({
          ...s,
          state: { ...s.state, [id]: again ? { ...next, due: now } : next },
          log: { ...s.log, [now]: { seen: l.seen + 1, fresh: l.fresh + (prev ? 0 : 1), again: l.again + (g === 1 ? 1 : 0) } },
        })
      })
      setQueue((q) => {
        const rest = q.filter((x) => x !== id)
        if (again) rest.splice(Math.min(3, rest.length), 0, id)
        return rest
      })
      setLean(null)
      setStep((n) => n + 1)
    },
    [now, keep],
  )

  const onLean = useCallback((id: string, g: Grade | null) => setLean(g ? { id, g } : null), [])
  const onDemoEnd = useCallback(() => {
    demoOn.current = false
    setDemo(false)
    setLean(null)
    setSaved(keep(start.saved))
    setQueue(start.queue)
    setStep((n) => n + 1)
  }, [keep, start])

  const onMore = () => {
    setExtra(extra + 5)
    setQueue(buildQueue(saved, now, newPerDay, extra + 5))
  }
  const onSettings = (patch: Partial<Saved["settings"]>) => {
    const next = keep({ ...saved, settings: { ...saved.settings, ...patch } })
    setSaved(next)
    if (patch.newPerDay !== undefined && patch.newPerDay !== newPerDay) setQueue(buildQueue(next, now, patch.newPerDay, extra))
  }
  const onImport = (file: Saved) => {
    const next = keep(merge(saved, file))
    setSaved(next)
    setQueue(buildQueue(next, now, next.settings.newPerDay ?? config.newPerDay, extra))
    setStep((n) => n + 1)
  }

  const ahead = useMemo(() => {
    if (!lean) return forecast(saved, now, queue, newPerDay)
    const again = comesBackToday(lean.g)
    const next = graded(saved.state[lean.id], lean.g, now)
    const s = { ...saved, state: { ...saved.state, [lean.id]: again ? { ...next, due: now } : next } }
    return forecast(s, now, again ? queue : queue.filter((x) => x !== lean.id), newPerDay)
  }, [saved, now, queue, newPerDay, lean])
  const t = useMemo(() => totals(saved, now, queue.length), [saved, now, queue.length])
  const days = ahead.days
  const doneToday = saved.log[now]?.seen ?? 0
  const moreLeft = config.cards.filter((c) => !saved.state[c.id] && !queue.includes(c.id)).length

  const go = (v: View) => {
    window.location.hash = `/${v}`
    setView(v)
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-3 px-4 lg:h-16 lg:px-8">
          <Logo />
          <h1 className="min-w-0 truncate text-base font-semibold lg:text-lg">{config.deckName}</h1>
          <nav className="ml-6 hidden items-center gap-1 short:flex lg:flex" aria-label="Screens">
            {VIEWS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => go(id)}
                aria-current={view === id ? "page" : undefined}
                className="flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground aria-[current=page]:bg-secondary aria-[current=page]:text-foreground"
              >
                <Icon className="size-4" />
                {label}
              </button>
            ))}
          </nav>
          <div className="tnum ml-auto shrink-0 text-sm text-muted-foreground">
            <span className="font-semibold text-foreground">{doneToday}</span> done · <span className="font-semibold text-foreground">{queue.length}</span> to go
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-[1400px] flex-1 flex-col px-4 pt-3 pb-[calc(80px+env(safe-area-inset-bottom))] short:pb-3 lg:px-8 lg:pt-6 lg:pb-8">
        {view === "study" ? (
          <div className="flex flex-1 flex-col gap-3 short:grid short:grid-cols-[minmax(0,1fr)_300px] short:grid-rows-[auto_minmax(0,1fr)] short:gap-x-6 lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-8">
            <section className="paper paper-phone mb-1 short:col-start-2 short:row-start-1 short:mb-0 lg:hidden">
              <div className="paper-head text-xs">
                <span className={`face-font-${config.font} text-[15px] font-semibold`}>Next 30 days</span>
                <span className="tnum text-face-soft">{ahead.cards} of {t.cards} cards</span>
              </div>
              <div className="pt-1">
                <ForecastChart days={days} height={40} labels={false} grow={demo} />
              </div>
              <div className="paper-row justify-between text-xs">
                <span className={`face-font-${config.font} text-[15px] font-semibold`}>Last 30 days</span>
                <span className="tnum text-face-soft">{t.answers30} answered · {t.streak} day streak</span>
              </div>
              <div className="paper-row pb-[4px]">
                <HeatRow log={saved.log} now={now} days={30} animate={demo} />
              </div>
            </section>

            <div className="flex flex-1 flex-col justify-center gap-5 short:contents lg:justify-start">
              <Progress done={doneToday} left={queue.length} />
              <StudyDeck
                queue={queue}
                state={saved.state}
                now={now}
                typing={typing}
                font={config.font}
                demo={demo}
                step={step}
                onGrade={onGrade}
                onLean={onLean}
                onDemoEnd={onDemoEnd}
                onMore={onMore}
                moreLeft={moreLeft}
              />
            </div>

            <aside className="hidden flex-col gap-5 lg:flex">
              <section className="paper">
                <PaperHead title="Next 30 days" meta={`${ahead.cards} of ${t.cards} cards`} />
                <div className="pt-2">
                  <ForecastChart days={days} height={104} grow={demo} />
                </div>
                <div className="paper-row">
                  <ForecastKey />
                </div>
              </section>
              <section className="paper" data-ruled="no">
                <PaperHead title="Days studied" meta={`${t.streak} day streak`} />
                <div className="pt-3 pb-1">
                  <HeatWeeks log={saved.log} now={now} weeks={20} cell={15} animate={demo} />
                </div>
              </section>
              <section className="paper">
                <PaperHead title="Where you stand" meta={`${t.cards} cards`} />
                <Totals t={t} />
              </section>
            </aside>
          </div>
        ) : view === "browse" ? (
          <BrowseView state={saved.state} now={now} />
        ) : view === "forecast" ? (
          <ForecastView days={days} coming={ahead.cards} log={saved.log} now={now} totals={t} />
        ) : (
          <SettingsView saved={saved} newPerDay={newPerDay} typing={typing} onSettings={onSettings} onImport={onImport} />
        )}
      </main>

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t bg-background/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-md short:hidden lg:hidden" aria-label="Screens">
        <div className="grid grid-cols-4">
          {VIEWS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => go(id)}
              aria-current={view === id ? "page" : undefined}
              className="flex h-16 flex-col items-center justify-center gap-1 text-xs font-medium text-muted-foreground aria-[current=page]:text-foreground"
            >
              <Icon className="size-5" />
              {label}
            </button>
          ))}
        </div>
      </nav>
    </div>
  )
}

function PaperHead({ title, meta }: { title: string; meta: string }) {
  return (
    <div className="paper-head">
      <h2 className={`face-font-${config.font} text-lg font-semibold`}>{title}</h2>
      <span className="tnum text-sm text-face-soft">{meta}</span>
    </div>
  )
}

function Progress({ done, left }: { done: number; left: number }) {
  const all = Math.max(1, done + left)
  return (
    <div className="mx-auto hidden w-full max-w-[760px] items-center gap-3 lg:flex">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
        <div className="bar-due h-full rounded-full transition-[width] duration-500" style={{ width: `${(done / all) * 100}%` }} />
      </div>
      <span className="tnum text-sm text-muted-foreground">
        {done} of {done + left}
      </span>
    </div>
  )
}

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="size-7 shrink-0" aria-hidden="true">
      <rect x="7" y="4" width="20" height="14" rx="2.5" transform="rotate(8 17 11)" fill="var(--face-edge)" />
      <rect x="4" y="10" width="22" height="16" rx="2.5" fill="var(--face)" stroke="var(--face-edge)" />
      <rect x="4" y="14.5" width="22" height="1.6" fill="var(--face-rule)" />
      <rect x="8" y="19" width="12" height="1.4" rx="0.7" fill="var(--face-ink)" opacity="0.55" />
      <rect x="8" y="22" width="8" height="1.4" rx="0.7" fill="var(--face-ink)" opacity="0.35" />
    </svg>
  )
}
