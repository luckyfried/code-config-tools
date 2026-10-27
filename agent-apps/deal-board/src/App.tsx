import { PlusIcon, Settings2Icon } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react"
import { flushSync } from "react-dom"
import { Board, revealStage } from "@/components/Board"
import { DealSheet } from "@/components/DealSheet"
import { Funnel } from "@/components/Funnel"
import { Headline } from "@/components/Headline"
import { ListView } from "@/components/ListView"
import { LostDrawer } from "@/components/LostDrawer"
import { ResultsView } from "@/components/ResultsView"
import { SettingsDialog } from "@/components/SettingsDialog"
import { Legend, WonLostChart } from "@/components/WonLostChart"
import { Button } from "@/components/ui/button"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { config } from "@/config"
import { SHORT, WIDE, useMedia } from "@/hooks/use-media"
import { changeWithMotion, describe } from "@/lib/actions"
import { plural } from "@/lib/format"
import { reducedMotion } from "@/lib/motion"
import { LOST, WON, latestMoves, moveDeal, newDeal, results, rewind, type Deal, type Move } from "@/lib/pipeline"
import { getDeals, setDeals, updateDeal, useDeals } from "@/lib/store"
import { cn } from "@/lib/utils"

type Route = "board" | "list" | "results"
const ROUTES: { id: Route; label: string }[] = [
  { id: "board", label: "Board" },
  { id: "list", label: "List" },
  { id: "results", label: "Won and lost" },
]

const routeOf = (): Route => {
  const hash = window.location.hash.replace(/^#\/?/, "")
  return hash === "list" || hash === "results" ? hash : "board"
}
const useRoute = () =>
  useSyncExternalStore(
    (change) => {
      window.addEventListener("hashchange", change)
      return () => window.removeEventListener("hashchange", change)
    },
    routeOf,
  )
const go = (route: Route) => {
  window.location.hash = route === "board" ? "" : `/${route}`
}

/** The newest move this browser has already shown, so a reload never replays what the person has seen. */
const SEEN = "deal-board:seen"
const wait = (ms: number) => new Promise((done) => setTimeout(done, ms))

function markSeen(at: number) {
  try {
    if (at > Number(localStorage.getItem(SEEN) ?? 0)) localStorage.setItem(SEEN, String(at))
  } catch {
    // Without storage the board replays its latest day on each visit, which is harmless.
  }
}

interface Step {
  deal: Deal
  move: Move
}

/** The latest day's moves this browser has not shown yet: the board opens a step behind and plays them, so it opens in motion on what changed. */
function planReplay(route: Route): Step[] {
  let seen = 0
  try {
    seen = Number(localStorage.getItem(SEEN) ?? 0)
  } catch {
    // As above.
  }
  const steps = latestMoves(getDeals()).filter(({ move }) => move.at > seen)
  if (steps.length > 0) markSeen(Math.max(...steps.map(({ move }) => move.at)))
  if (route !== "board" || reducedMotion()) return []
  return steps
}

export default function App() {
  const deals = useDeals()
  const route = useRoute()
  const wide = useMedia(WIDE)
  const short = useMedia(SHORT) && !wide
  const now = useMemo(() => Date.now(), [deals]) // eslint-disable-line react-hooks/exhaustive-deps
  const [replay, setReplay] = useState<Step[]>(() => planReplay(routeOf()))
  const stopped = useRef(false)
  const [status, setStatus] = useState(() => {
    const last = latestMoves(getDeals(), 1)[0]
    return last ? describe(last.deal, last.move, Date.now()) : ""
  })
  const [sheet, setSheet] = useState<string | "new" | null>(null)
  const [lostOpen, setLostOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)

  const shown = useMemo(
    () => (replay.length === 0 ? deals : rewind(deals, replay.map((step) => step.move), replay.map((step) => step.deal.id))),
    [deals, replay],
  )

  const finishReplay = useCallback(() => {
    stopped.current = true
    setReplay([])
  }, [])

  useEffect(() => {
    if (replay.length === 0) return
    const steps = replay
    stopped.current = false
    let cancelled = false
    void (async () => {
      const first = steps[0]
      // The board opens on the first stage that changes, and the first move starts as soon as the page has settled.
      await revealStage(first.move.to === WON || first.move.to === LOST ? (first.move.from ?? "") : first.move.to, false)
      await wait(700)
      for (const step of steps) {
        if (cancelled || stopped.current) return
        const { deal, move } = step
        const closing = move.to === WON || move.to === LOST
        await revealStage(closing ? (move.from ?? "") : move.to)
        if (cancelled || stopped.current) return
        changeWithMotion(deal.id, move.to, () => setReplay((left) => left.filter((s) => s !== step)))
        setStatus(describe(deal, move, Date.now()))
        // After the first move the board rests a while, so the flight and the new total can be taken in before the next.
        await wait(step === steps[0] ? 3000 : closing ? 1500 : 1300)
      }
    })()
    return () => {
      cancelled = true
    }
    // The replay runs once, on the steps planned at load.
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (route !== "board") finishReplay()
  }, [route, finishReplay])

  const moveTo = useCallback(
    (id: string, to: string, from?: DOMRect) => {
      finishReplay()
      const deal = getDeals().find((d) => d.id === id)
      if (!deal || deal.stage === to) return
      const at = Date.now()
      const moved = moveDeal(deal, to, at)
      markSeen(at)
      changeWithMotion(id, to, () => updateDeal(id, () => moved), from)
      setStatus(describe(moved, moved.log[moved.log.length - 1]))
    },
    [finishReplay],
  )

  /** A stage change made in the deal sheet: on a phone the sheet steps aside first so the move can be seen. */
  const moveFromSheet = useCallback(
    async (id: string, to: string) => {
      const deal = getDeals().find((d) => d.id === id)
      if (!deal) return
      const closing = to === WON || to === LOST
      if (closing || !wide) {
        flushSync(() => setSheet(null))
        await wait(260)
        if (route === "board") await revealStage(deal.stage)
      }
      moveTo(id, to)
    },
    [moveTo, route, wide],
  )

  const sheetDeal = sheet === null ? null : sheet === "new" ? "new" : (deals.find((deal) => deal.id === sheet) ?? null)
  const r = results(shown, now)

  const band = (
    <div className={cn("grid shrink-0 gap-x-10 gap-y-5", wide ? "grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)_minmax(0,1.1fr)] px-6 pt-2 pb-5" : short ? "grid-cols-2 items-center px-4 pt-1 pb-4" : "px-4 pt-1 pb-4")}>
      <Headline deals={shown} stages={config.stages} status={status} compact={!wide} />
      {wide ? (
        <>
          <section aria-label="Funnel" className="flex flex-col gap-3 border-l border-band-border pl-8">
            <h2 className="text-[13px] font-medium text-muted-foreground">Funnel, deals in each stage</h2>
            <Funnel deals={shown} stages={config.stages} />
          </section>
          <section aria-label="Won and lost, last 90 days" className="flex flex-col gap-3 border-l border-band-border pl-8">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <h2 className="text-[13px] font-medium text-muted-foreground">Won and lost, last 90 days</h2>
              <Legend won={r.wonValue} lost={r.lostValue} />
            </div>
            <WonLostChart weeks={r.weeks} className="flex-1" />
            <p className="flex gap-5 text-[13px] text-muted-foreground">
              <span>
                Win rate <span className="font-semibold text-foreground tabular-nums">{r.winRate === null ? "none yet" : `${Math.round(r.winRate * 100)}%`}</span>
              </span>
              <span>
                Average cycle <span className="font-semibold text-foreground tabular-nums">{r.averageCycle === null ? "none yet" : plural(Math.round(r.averageCycle), "day")}</span>
              </span>
            </p>
          </section>
        </>
      ) : (
        <Funnel deals={shown} stages={config.stages} compact onPick={(id) => void revealStage(id)} />
      )}
    </div>
  )

  return (
    <TooltipProvider>
      <div className="flex h-dvh flex-col overflow-hidden bg-background pl-[env(safe-area-inset-left)] pr-[env(safe-area-inset-right)]">
        <header className={cn("flex shrink-0 items-center gap-3 pt-[max(env(safe-area-inset-top),0.75rem)] pb-2", wide ? "px-6" : "px-4")}>
          <BoardMark />
          <h1 className="-ml-1 min-w-0 truncate text-lg font-semibold tracking-[-0.015em]">{config.name}</h1>
          <nav aria-label="Views" className="hidden items-center gap-1 rounded-xl bg-muted p-1 sm:ml-6 sm:flex">
            {ROUTES.map((item) => (
              <a
                key={item.id}
                href={item.id === "board" ? "#" : `#/${item.id}`}
                aria-current={route === item.id ? "page" : undefined}
                className={cn(
                  "rounded-lg px-3.5 py-1.5 text-sm font-medium text-muted-foreground transition-colors duration-150 hover:text-foreground",
                  route === item.id && "bg-background text-foreground shadow-card",
                )}
              >
                {item.label}
              </a>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <Button onClick={() => setSheet("new")} className="max-sm:hidden">
              <PlusIcon data-icon="inline-start" />
              Add deal
            </Button>
            <Button size="icon" onClick={() => setSheet("new")} className="sm:hidden" aria-label="Add deal">
              <PlusIcon />
            </Button>
            <Button size="icon" variant="ghost" onClick={() => setSettingsOpen(true)} aria-label="Settings">
              <Settings2Icon />
            </Button>
          </div>
        </header>

        <main className={cn("flex min-h-0 flex-1 flex-col", route === "board" && !short ? "" : "overflow-y-auto")}>
          {route === "board" ? (
            <>
              {wide ? <div className="mx-6 mb-4 h-px shrink-0 bg-band-border" /> : null}
              {band}
              <Board
                deals={shown}
                stages={config.stages}
                now={now}
                won={{ count: r.won, value: r.wonValue }}
                onOpen={(id) => {
                  finishReplay()
                  setSheet(id)
                }}
                onMove={moveTo}
                onOpenLost={() => setLostOpen(true)}
                onOpenWon={() => go("results")}
                onDragStarted={finishReplay}
                short={short}
              />
            </>
          ) : route === "list" ? (
            <ListView deals={deals} stages={config.stages} now={now} onOpen={setSheet} />
          ) : (
            <ResultsView deals={deals} stages={config.stages} now={now} onOpen={setSheet} />
          )}
        </main>

        <nav aria-label="Views" className="grid shrink-0 grid-cols-3 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] sm:hidden">
          {ROUTES.map((item) => (
            <a
              key={item.id}
              href={item.id === "board" ? "#" : `#/${item.id}`}
              aria-current={route === item.id ? "page" : undefined}
              className={cn("flex h-14 items-center justify-center text-[15px] font-medium text-muted-foreground", route === item.id && "text-foreground")}
            >
              <span className={cn("rounded-full px-3 py-1.5", route === item.id && "bg-muted")}>{item.label}</span>
            </a>
          ))}
        </nav>
      </div>

      <DealSheet
        deal={sheetDeal}
        stages={config.stages}
        defaultStage={config.stages[0]?.id ?? ""}
        now={now}
        onClose={() => setSheet(null)}
        onCreate={(draft) => {
          const deal = newDeal(draft, Date.now())
          setDeals((current) => [...current, deal])
          setSheet(null)
          setStatus(`${deal.company} joined ${config.stages.find((s) => s.id === deal.stage)?.label ?? "the board"}.`)
        }}
        onChange={(id, change) => updateDeal(id, (deal) => ({ ...deal, ...change }))}
        onStage={(id, to) => void moveFromSheet(id, to)}
        onDelete={(id) => setDeals((current) => current.filter((deal) => deal.id !== id))}
      />
      <LostDrawer
        open={lostOpen}
        onOpenChange={setLostOpen}
        deals={deals}
        stages={config.stages}
        now={now}
        onReopen={(id, to) => {
          setLostOpen(false)
          setTimeout(() => moveTo(id, to), 260)
        }}
        onOpenDeal={(id) => {
          setLostOpen(false)
          setSheet(id)
        }}
      />
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
      <Toaster position={wide ? "bottom-right" : "top-center"} />
    </TooltipProvider>
  )
}

/** The board's own mark beside its title: the funnel in three bars, in the first, middle, and last stages' colors. */
function BoardMark() {
  const stages = config.stages
  const picks = [stages[0], stages[Math.floor((stages.length - 1) / 2)], stages[stages.length - 1]]
  return (
    <svg viewBox="0 0 24 24" className="size-6 shrink-0" aria-hidden="true">
      {picks.map((stage, i) => (
        <rect
          key={i}
          data-stage=""
          style={{ "--stage-raw": stage?.color, fill: "var(--stage)" } as React.CSSProperties}
          x={2 + i * 3.5}
          y={3.5 + i * 6.5}
          width={20 - i * 7}
          height="4.5"
          rx="2.25"
        />
      ))}
    </svg>
  )
}
