import { useEffect, useMemo, useState } from "react"
import { Deck } from "@/components/deck"
import { JobCard } from "@/components/job-card"
import { JobDetail } from "@/components/job-detail"
import { LaneBody } from "@/components/lane-body"
import { useBoard } from "@/hooks/use-board"
import { useMedia } from "@/hooks/use-media"
import { lastChecked, movedAt, when } from "@/lib/board"
import { hue } from "@/lib/company"
import { reduced } from "@/lib/motion"
import { cn } from "@/lib/utils"
import type { AppConfig, Card, Status } from "@/types"

declare global {
  interface Window {
    __APP_CONFIG__?: AppConfig
  }
}

const LANE: Record<Status, { title: string; empty: string }> = {
  new: { title: "New", empty: "Everything new has a choice. Ask your agent to look for more." },
  yes: { title: "Yes", empty: "Press Y on a card you want." },
  later: { title: "Later", empty: "Press L on a card to keep it for later." },
  no: { title: "No", empty: "Nothing passed on yet." },
}
const PHONE_LANE: Record<Status, string> = {
  new: "Swipe right for yes, left for no.",
  yes: "Tap Apply and your agent asks you before it sends anything.",
  later: "Waiting for a second look.",
  no: "Passed on. Swipe right to bring one back as a yes.",
}

// One track per lane shown; the pile of new openings is the widest.
const TRACKS = ["", "grid-cols-1", "grid-cols-[1.3fr_1fr]", "grid-cols-[1.25fr_1fr_1fr]", "grid-cols-[1.2fr_1fr_1fr_1fr]"]

const fallback: AppConfig = { name: "", ask: "", columns: ["new", "yes", "later"], theme: "auto", sample: [] }

export default function App() {
  const config = useMemo(() => window.__APP_CONFIG__ ?? fallback, [])
  // A phone on its side is still a phone: one column at a time, beside the header.
  const phone = useMedia("(max-width: 767px), (max-height: 520px)")
  const { mode, cards, events, cardProblem, busy, viewOnly, choose } = useBoard(config)
  const [openId, setOpenId] = useState<string | null>(null)
  const [showNo, setShowNo] = useState(false)
  const [tab, setTab] = useState<Status>(config.columns[0] ?? "new")
  // The board opens in its own time: the header first, then, once the type has loaded, the cards rise in column by
  // column. Until then every card waits, hidden, where it will land.
  const [intro, setIntro] = useState(true)
  const [go, setGo] = useState(false)
  useEffect(() => {
    if (mode === "loading") return
    let done = 0
    let stop = false
    const start = () => {
      if (stop || done) return
      setGo(true)
      done = window.setTimeout(() => setIntro(false), reduced() ? 0 : 2400)
    }
    const cap = window.setTimeout(start, 900)
    const type = ['600 1rem "Bricolage Grotesque Variable"', '400 1rem "Public Sans Variable"'].map((f) => document.fonts.load(f))
    void Promise.all(type).finally(() => {
      window.clearTimeout(cap)
      start()
    })
    return () => {
      stop = true
      window.clearTimeout(cap)
      window.clearTimeout(done)
    }
  }, [mode])

  const live = mode === "live"
  // The pile keeps the order the agent found them in; a sorted column shows the newest move on top.
  const by = (s: Status) => {
    const list = cards.filter((c) => c.shown === s)
    return s === "new" ? list : list.toSorted((a, b) => movedAt(b).localeCompare(movedAt(a)))
  }
  const checked = lastChecked(events)
  const statusLine = checked ? `The agent last checked ${when(checked)}.` : "The agent checks when you ask."
  const open = cards.find((c) => c.record.id === openId) ?? null
  const passed = by("no").length
  const lanes = config.columns.filter((s) => s !== "no" || showNo || config.columns.includes("no"))
  if (showNo && !lanes.includes("no")) lanes.push("no")
  // Each card's turn in the opening: the columns left to right, the pile from its bottom card up.
  const order = new Map<string, number>()
  for (const s of phone ? [tab] : lanes) {
    const list = by(s)
    for (const c of s === "new" ? list.slice(0, 3).reverse() : list) order.set(c.record.id, order.size)
  }
  const title = config.name ? `${config.name}'s job board` : "Job board"
  useEffect(() => {
    document.title = title
  }, [title])

  const onChoose = (card: Card, action: Parameters<typeof choose>[1], fromX?: number) => void choose(card, action, fromX)

  // On a desktop Y, N, and L take the focused card, and the top of the pile when no card holds the focus.
  const top = by("new")[0]
  useEffect(() => {
    if (phone || !top || openId) return
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || e.repeat || e.target !== document.body) return
      const key = e.key.toLowerCase()
      if (key !== "y" && key !== "n" && key !== "l") return
      e.preventDefault()
      void choose(top, key === "y" ? "yes" : key === "n" ? "no" : "later")
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [phone, top, openId, choose])

  if (mode === "loading") return <div className="h-dvh bg-background" />

  const header = (
    <header className={cn("rise flex gap-x-10 gap-y-3", phone ? "flex-col pt-4 pb-2 pad-safe" : "items-end justify-between px-8 pt-7 pb-5")}>
      <div className="min-w-0">
        <p className="text-sm font-semibold tracking-wide text-muted-foreground">{title}</p>
        {config.ask && (
          <h1
            className={cn(
              "mt-1 font-heading font-semibold tracking-[-0.02em] text-balance",
              phone ? "line-clamp-3 text-[1.3125rem]/[1.18]" : "max-w-[52rem] text-[2rem]/[1.12]",
            )}
          >
            {config.ask}
          </h1>
        )}
      </div>
      <div className={cn("flex flex-wrap items-center gap-x-3 gap-y-1.5 text-sm", !phone && "shrink-0 justify-end text-right")}>
        <span className="text-muted-foreground">{statusLine}</span>
        {!phone && !config.columns.includes("no") && (
          <button
            type="button"
            data-pile="no"
            onClick={() => setShowNo((v) => !v)}
            aria-pressed={showNo}
            className="rounded-full bg-secondary px-3 py-1 font-semibold text-secondary-foreground tabular-nums transition-colors hover:bg-accent"
          >
            {showNo ? "Hide passed" : `${passed} passed`}
          </button>
        )}
      </div>
    </header>
  )

  const cardFor = (c: Card, i: number) => (
    <JobCard
      key={c.record.id}
      card={c}
      variant="compact"
      index={order.get(c.record.id) ?? i}
      intro={intro}
      live={live}
      phone={phone}
      problem={cardProblem[c.record.id]}
      viewOnly={viewOnly === c.record.id}
      busy={!!busy[c.record.id]}
      onChoose={onChoose}
      onOpen={(x) => setOpenId(x.record.id)}
    />
  )

  const heroFor = (c: Card, depth: number) => (
    <JobCard
      key={c.record.id}
      card={c}
      variant="hero"
      depth={depth}
      index={order.get(c.record.id) ?? depth}
      intro={intro}
      live={live}
      phone={phone}
      problem={cardProblem[c.record.id]}
      viewOnly={viewOnly === c.record.id}
      busy={!!busy[c.record.id]}
      onChoose={onChoose}
      onOpen={(x) => setOpenId(x.record.id)}
    />
  )

  const detail = (onPhone: boolean) => (
    <JobDetail
      card={open}
      phone={onPhone}
      busy={!!open && !!busy[open.record.id]}
      problem={open ? cardProblem[open.record.id] : undefined}
      viewOnly={!!open && viewOnly === open.record.id}
      onClose={() => setOpenId(null)}
      onChoose={onChoose}
    />
  )

  if (phone) {
    const tabs = [...config.columns.filter((s) => s !== "no"), "no" as const]
    const list = by(tab)
    return (
      <div className="phone-shell flex min-h-dvh flex-col" data-go={go || undefined}>
        <div className="phone-side">
        {header}
        <nav className="sticky top-0 z-10 bg-background/90 py-2 backdrop-blur-md pad-safe" aria-label="Columns">
          <div className="grid auto-cols-fr grid-flow-col gap-1 rounded-xl bg-secondary p-1">
            {tabs.map((s) => (
              <button
                key={s}
                type="button"
                data-pile={s}
                onClick={() => setTab(s)}
                aria-pressed={tab === s}
                className={cn(
                  "flex h-10 items-center justify-center gap-1.5 rounded-lg text-[0.9375rem] font-semibold transition-colors",
                  tab === s ? "tab-on text-foreground" : "text-muted-foreground",
                )}
              >
                {LANE[s].title}
                <span key={by(s).length} className="count-pop text-[0.8125rem] font-medium text-muted-foreground tabular-nums">
                  {by(s).length}
                </span>
              </button>
            ))}
          </div>
        </nav>
        {list[0] && <Brief key={list[0].record.id} card={list[0]} />}
        </div>
        <main className="phone-main flex flex-1 flex-col gap-3 pt-2 pb-4 pad-safe">
          <p className="swipe-hint text-[0.8125rem] text-muted-foreground">{PHONE_LANE[tab]}</p>
          {tab === "new" ? (
            <Deck cards={list} empty={LANE.new.empty} render={heroFor} />
          ) : (
            <>
              {list.map(cardFor)}
              {list.length === 0 && <p className="py-10 text-center text-muted-foreground">{LANE[tab].empty}</p>}
            </>
          )}
        </main>
        {detail(true)}
      </div>
    )
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden" data-go={go || undefined}>
      {header}
      <main
        className={cn(
          "grid min-h-0 flex-1 gap-4 px-8",
          "pb-7",
          TRACKS[Math.min(lanes.length, 4)],
        )}
      >
        {lanes.map((s) => {
          const list = by(s)
          return (
            <section key={s} className="lane flex min-h-0 flex-col rounded-2xl" aria-label={LANE[s].title} data-pile={s}>
              <div className="flex items-baseline justify-between px-4 pt-3.5 pb-2.5">
                <h2 className="font-heading text-lg font-semibold">{LANE[s].title}</h2>
                <span key={list.length} className="count-pop text-sm font-semibold text-muted-foreground tabular-nums">
                  {list.length}
                </span>
              </div>
              {s === "new" ? (
                <div className="lane-deck min-h-0 flex-1 overflow-y-auto px-3 pt-1 pb-4">
                  <Deck cards={list} empty={LANE.new.empty} render={heroFor} />
                </div>
              ) : (
              <LaneBody
                size={list.length}
                className="lane-scroll min-h-0 flex-1 overflow-y-auto px-3"
              >
                {list.map(cardFor)}
                {list.length === 0 && <p className="px-2 py-6 text-sm text-muted-foreground">{LANE[s].empty}</p>}
              </LaneBody>
              )}
            </section>
          )
        })}
      </main>
      {detail(false)}
    </div>
  )
}

// A phone on its side has room beside the card: the facts that made it worth a look and the agent's word on it sit
// under the tabs, next to the card they belong to.
function Brief({ card }: { card: Card }) {
  const { job } = card
  if (job.facts.length === 0 && !job.agent_notes[0]) return null
  return (
    <section
      className="brief pad-safe"
      aria-label={`Why ${job.company}`}
      ref={(el) => el?.style.setProperty("--hue", String(hue(job.company)))}
    >
      <p className="text-[0.8125rem] font-semibold text-muted-foreground">Why {job.company}</p>
      {job.facts.length > 0 && (
        <ul className="facts mt-2 flex flex-col gap-1.5 text-[0.875rem] leading-snug text-pretty">
          {job.facts.slice(0, 2).map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
      )}
      {job.agent_notes[0] && (
        <p className="note mt-3 px-3 py-2 text-[0.8125rem] leading-snug text-pretty">
          <span className="font-semibold">Your agent: </span>
          {job.agent_notes[0]}
        </p>
      )}
    </section>
  )
}
