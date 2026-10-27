import { useCallback, useEffect, useMemo, useState } from "react"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { HomeCard } from "@/components/home-card"
import { HomeDetail } from "@/components/home-detail"
import { ComparePanel, CompareSheet, DesktopTray, PhoneTray } from "@/components/tray"
import { useBoard } from "@/hooks/use-board"
import { useMedia } from "@/hooks/use-media"
import { useTray } from "@/hooks/use-tray"
import { ago, column, COLUMN_NAMES, COLUMNS, lastChecked, priceLabel } from "@/lib/board"
import { flyTo, reduced, tiltShow } from "@/lib/motion"
import type { Action, AppConfig, Card, Status } from "@/types"

const FALLBACK: AppConfig = {
  name: "",
  ask: "",
  currency: "USD",
  units: "sqft",
  compare_rows: ["price", "price_per_area", "rooms", "baths", "area", "commute", "place"],
  theme: "auto",
  sample: [],
}
const config: AppConfig = { ...FALLBACK, ...(window.__APP_CONFIG__ ?? {}) }
const STARTER = (config.sample ?? []).filter((h) => h.status === "yes").slice(0, 2).map((h) => h.id)
const TOUR_ANSWER = "Replaced in 2021 with a 30-year roof; the seller's agent sent the invoice."

export default function App() {
  const phone = useMedia("(max-width: 860px)")
  const board = useBoard(config, phone)
  const { cards, mode } = board
  const live = mode === "live"
  const tray = useTray(STARTER)
  const [openId, setOpenId] = useState<string | null>(null)
  const [focus, setFocus] = useState<"ask" | undefined>(undefined)
  const [tab, setTab] = useState<Status>("new")
  const [passedOpen, setPassedOpen] = useState(false)
  const [, setClock] = useState(0)

  useEffect(() => {
    const t = window.setInterval(() => setClock((n) => n + 1), 30000)
    return () => window.clearInterval(t)
  }, [])

  const byId = useMemo(() => new Map(cards.map((c) => [c.id, c])), [cards])
  const trayCards = tray.tray.map((id) => byId.get(id)).filter((c): c is Card => c != null)
  const cols = useMemo(() => Object.fromEntries(COLUMNS.map((s) => [s, column(cards, s)])) as Record<Status, Card[]>, [cards])
  const passed = useMemo(() => column(cards, "no"), [cards])
  const checked = lastChecked(board.events)

  // A home that left the board (the agent replaced the sample) leaves the tray too.
  const { save, tray: trayIds } = tray
  useEffect(() => {
    if (mode !== "live" || cards.length === 0) return
    const keep = trayIds.filter((id) => byId.has(id))
    if (keep.length !== trayIds.length) save(keep)
  }, [mode, cards.length, byId, trayIds, save])

  const open = useCallback((id: string, f?: "ask") => {
    setFocus(f)
    setOpenId(id)
  }, [])
  const choose = useCallback(
    (card: Card, action: Action, from?: { x: number; y: number }) => void board.choose(card, action, from),
    [board],
  )
  const onTray = useCallback(
    async (id: string) => {
      if (tray.tray.includes(id)) return tray.remove(id)
      if (tray.tray.length < 3) await flyTo(id, document.querySelector("[data-slot-empty]"))
      tray.add(id)
    },
    [tray],
  )

  // The tour: with no runtime behind the page, a desktop shows once what the board does, after it has settled.
  const { demoMove, demoAnswer, cardsRef } = board
  const { add: trayAdd, show: trayShow } = tray
  useEffect(() => {
    if (mode !== "sample" || phone || reduced()) return
    const timers: number[] = []
    const at = (ms: number, run: () => void) => timers.push(window.setTimeout(run, ms))
    const fresh = () => column(cardsRef.current, "new")
    at(2100, () => {
      const c = fresh()[0]
      if (c) void tiltShow(c.id)
    })
    at(3000, () => {
      const c = cardsRef.current.find((x) => x.shown !== "no" && x.home.questions.some((q) => q.answer == null))
      if (c) demoAnswer(c.id, TOUR_ANSWER)
    })
    at(3900, () => {
      const c = fresh()[0]
      if (c) void demoMove(c, "yes")
    })
    at(5300, () => {
      const c = fresh()[1]
      if (c) void demoMove(c, "no")
    })
    at(6500, () => {
      const c = fresh()[0]
      if (c) void demoMove(c, "maybe")
    })
    at(7500, async () => {
      const c = column(cardsRef.current, "yes")[0]
      if (!c) return
      await flyTo(c.id, document.querySelector("[data-slot-empty]"))
      trayAdd(c.id, false)
    })
    at(8350, () => {
      const ids = column(cardsRef.current, "yes").slice(0, 3).map((c) => c.id)
      trayShow(ids, false)
    })
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [mode, phone, cardsRef, demoAnswer, demoMove, trayAdd, trayShow])

  const status = live ? (checked ? `Your agent last checked ${ago(checked)}.` : "The agent checks when you ask.") : mode === "sample" ? "Sample homes" : null
  const who = config.name ? `${config.name}'s home hunt` : "Home hunt"
  const openCard = openId ? (byId.get(openId) ?? null) : null
  const cardProps = (c: Card, i: number) => ({
    card: c,
    config,
    index: i,
    phone,
    live,
    inTray: tray.tray.includes(c.id),
    problem: board.problem[c.id],
    busy: !!board.busy[c.id],
    onChoose: choose,
    onTray,
    onOpen: open,
  })

  return (
    <div className="app" data-phone={phone ? "" : undefined} data-mode={mode}>
      <header className="top pad-safe">
        <div className="top-text">
          <p className="eyebrow">Home Hunt</p>
          <h1>{who}</h1>
          {config.ask && <p className="ask-line">{config.ask}</p>}
        </div>
        <div className="status">
          {status && (
            <p className="status-line" data-live={live ? "" : undefined}>
              <span className="pulse" aria-hidden="true" />
              {status}
            </p>
          )}
          <button type="button" className="passed-btn" onClick={() => setPassedOpen(true)} key={passed.length}>
            <span className="n">{passed.length}</span> passed
          </button>
        </div>
      </header>

      {phone ? (
        <>
          <nav className="tabs pad-safe" aria-label="Columns">
            {COLUMNS.map((s) => (
              <button key={s} type="button" className="tab" aria-pressed={tab === s} onClick={() => setTab(s)}>
                {COLUMN_NAMES[s]} <span className="count">{cols[s].length}</span>
              </button>
            ))}
            <button type="button" className="tab tab-no" onClick={() => setPassedOpen(true)} aria-label={`${passed.length} passed`}>
              No <span className="count">{passed.length}</span>
            </button>
          </nav>
          <main className="phone-list pad-safe" data-col={tab}>
            {cols[tab].map((c, i) => (
              <HomeCard key={c.id} {...cardProps(c, i)} />
            ))}
            {mode !== "loading" && cols[tab].length === 0 && <p className="lane-empty">{EMPTY[tab]}</p>}
          </main>
          <PhoneTray cards={trayCards} onRemove={tray.remove} onCompare={() => tray.show(tray.tray)} />
          <CompareSheet
            open={tray.open && trayCards.length >= 2}
            cards={trayCards}
            config={config}
            onRemove={tray.remove}
            onOpen={open}
            onClose={tray.hide}
          />
        </>
      ) : (
        <main className="board pad-safe">
          {COLUMNS.map((s) => (
            <section key={s} className={`lane lane-${s}`} aria-label={COLUMN_NAMES[s]}>
              <h2 className="lane-head">
                {COLUMN_NAMES[s]} <span className="count">{cols[s].length}</span>
              </h2>
              <div className="lane-scroll">
                <div className="lane-cards">
                  {cols[s].map((c, i) => (
                    <HomeCard key={c.id} {...cardProps(c, s === "new" ? i : i + 2)} />
                  ))}
                  {mode !== "loading" && cols[s].length === 0 && <p className="lane-empty">{EMPTY[s]}</p>}
                </div>
              </div>
            </section>
          ))}
          <DesktopTray cards={trayCards} config={config} onAdd={(id) => void onTray(id)} onRemove={tray.remove} onCompare={() => tray.show(tray.tray)} />
          {tray.open && trayCards.length >= 2 && (
            <ComparePanel cards={trayCards} config={config} onRemove={tray.remove} onOpen={open} onClose={tray.hide} />
          )}
        </main>
      )}

      <HomeDetail
        card={openCard}
        config={config}
        phone={phone}
        live={live}
        focus={focus}
        inTray={openCard ? tray.tray.includes(openCard.id) : false}
        onClose={() => setOpenId(null)}
        onChoose={choose}
        onNote={board.note}
        onAsk={board.ask}
        onTray={(id) => void onTray(id)}
      />

      <Sheet open={passedOpen} onOpenChange={setPassedOpen}>
        <SheetContent side={phone ? "bottom" : "right"} className="passed-sheet">
          <SheetHeader>
            <SheetTitle className="font-heading text-xl">Passed</SheetTitle>
            <SheetDescription>The homes you said no to. Change your mind on any of them here.</SheetDescription>
          </SheetHeader>
          <ul className="passed-list">
            {passed.map((c) => (
              <li key={c.id}>
                <div className="thumb" style={{ background: c.home.color }}>
                  {c.home.image && <img src={c.home.image} alt="" />}
                </div>
                <div className="pl-text">
                  <button type="button" onClick={() => open(c.id)}>
                    {c.home.title}
                  </button>
                  <p>
                    {priceLabel(c.home, config.currency)} · {c.home.place}
                  </p>
                </div>
                <div className="pl-acts">
                  <button type="button" className="act act-maybe" aria-disabled={!live ? true : undefined} onClick={() => choose(c, "maybe")}>
                    Maybe
                  </button>
                  <button type="button" className="act act-yes" aria-disabled={!live ? true : undefined} onClick={() => choose(c, "yes")}>
                    Yes
                  </button>
                </div>
              </li>
            ))}
            {passed.length === 0 && <li className="quiet">Nothing passed yet.</li>}
          </ul>
        </SheetContent>
      </Sheet>
    </div>
  )
}

const EMPTY: Record<Status, string> = {
  new: "Every new home has a choice. Your agent adds more as it finds them.",
  yes: "Homes you like land here.",
  maybe: "Homes you want to think over land here.",
  no: "",
}
