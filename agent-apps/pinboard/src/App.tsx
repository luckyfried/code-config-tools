import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { PinCard } from "@/components/pin-card"
import { PinDetail } from "@/components/pin-detail"
import { Shelves } from "@/components/shelves"
import { Button } from "@/components/ui/button"
import {
  cancelChoice,
  choiceKey,
  filterHash,
  isChangeOfMind,
  loadSnapshot,
  matches,
  postChoice,
  probeLive,
  readFilter,
  slug,
  viewPins,
  type Snapshot,
} from "@/lib/data"
import { flip, flyTo, measure, reducedMotion } from "@/lib/motion"
import { runSampleDemo } from "@/demo"
import type { Action, AppConfig, BoardBody, Filter, InboxEvent, Mode, PinBody, PinView, StoredRecord } from "@/types"

const config: AppConfig = window.__APP_CONFIG__ ?? { name: "", boards: [], theme: "auto", sample: [] }
const POLL_MS = 5000

/** `events` with each of `changes` put in place of the event with its id, or added. */
export function upsert(events: InboxEvent[], changes: InboxEvent[]): InboxEvent[] {
  const byId = new Map(events.map((event) => [event.id, event]))
  for (const change of changes) byId.set(change.id, change)
  return [...byId.values()]
}

function sampleSnapshot(holdFinds: boolean): Snapshot {
  const pins: StoredRecord<PinBody>[] = config.sample
    .filter((pin) => !(holdFinds && pin.found_for))
    .map((pin, n) => ({ id: pin.id, kind: "pins", revision: 1, at: "", body: { ...pin, added: String(n).padStart(4, "0") } }))
  const boards = config.boards.map((name) => ({ id: slug(name), kind: "boards", revision: 1, at: "", body: { id: slug(name), name } }))
  return { pins, boards, events: [] }
}

function preload(pins: StoredRecord<PinBody>[]): Promise<Map<string, number>> {
  const ratios = new Map<string, number>()
  const loads = pins.map(
    (pin) =>
      new Promise<void>((done) => {
        const img = new Image()
        img.onload = () => {
          if (img.naturalWidth && img.naturalHeight) ratios.set(pin.body.image, img.naturalWidth / img.naturalHeight)
          done()
        }
        img.onerror = () => done()
        img.src = pin.body.image
      }),
  )
  return Promise.race([Promise.all(loads), new Promise((done) => window.setTimeout(done, 600))]).then(() => ratios)
}

export default function App() {
  const [mode, setMode] = useState<Mode>("loading")
  const [snapshot, setSnapshot] = useState<Snapshot>({ pins: [], boards: [], events: [] })
  const [ratios, setRatios] = useState<Map<string, number>>(new Map())
  const [filter, setFilter] = useState<Filter>(() => readFilter(window.location.hash))
  const [detailId, setDetailId] = useState<string | null>(null)
  const [openId, setOpenId] = useState<string | null>(null)
  const [folding, setFolding] = useState<Set<string>>(new Set())
  const [errors, setErrors] = useState<Map<string, string>>(new Map())
  const [unreachable, setUnreachable] = useState(false)
  const [busy, setBusy] = useState<Set<string>>(new Set())
  const inFlight = useRef(new Set<string>())
  const installs = useRef(0)
  const cards = useRef(new Map<string, HTMLElement>())
  const shelves = useRef(new Map<string, HTMLElement>())
  const live = mode === "live" && !unreachable

  useEffect(() => {
    document.title = config.name ? `${config.name}'s boards` : "Pinboard"
    let stopped = false
    let timer = 0
    const start = async () => {
      if (await probeLive()) {
        const first = await loadSnapshot()
        if (stopped) return
        const snap = first ?? { pins: [], boards: [], events: [] }
        setRatios(await preload(snap.pins))
        setSnapshot(snap)
        setMode("live")
        timer = window.setInterval(async () => {
          const started = installs.current
          const next = await loadSnapshot()
          if (stopped) return
          setUnreachable(next === null)
          // A poll that a choice overtook carries the wall from before that choice, so it is dropped.
          if (next && started === installs.current && inFlight.current.size === 0) setSnapshot(next)
        }, POLL_MS)
        return
      }
      const demo = !reducedMotion()
      const snap = sampleSnapshot(demo)
      setRatios(await preload(sampleSnapshot(false).pins))
      if (stopped) return
      setSnapshot(snap)
      setMode("static")
      if (demo) runSampleDemo(config, { setSnapshot, setFolding, cards: cards.current, shelves: shelves.current, isStopped: () => stopped })
    }
    start()
    return () => {
      stopped = true
      window.clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    const onHash = () => setFilter(readFilter(window.location.hash))
    window.addEventListener("hashchange", onHash)
    return () => window.removeEventListener("hashchange", onHash)
  }, [])

  useEffect(() => {
    if (!openId) return
    const close = (event: PointerEvent) => {
      const card = cards.current.get(openId)
      if (card && event.target instanceof Node && card.contains(event.target)) return
      if (event.target instanceof Element && event.target.closest("[data-radix-popper-content-wrapper]")) return
      setOpenId(null)
    }
    document.addEventListener("pointerdown", close)
    return () => document.removeEventListener("pointerdown", close)
  }, [openId])

  const boards: BoardBody[] = useMemo(() => {
    const known = snapshot.boards.map((record) => record.body)
    for (const event of snapshot.events) {
      const id = event.payload.board
      if (event.action === "move" && id && event.status !== "cancelled" && !known.some((board) => board.id === id)) {
        known.push({ id, name: event.payload.name || id })
      }
    }
    return known
  }, [snapshot])
  const boardIds = useMemo(() => new Set(boards.map((board) => board.id)), [boards])
  const boardName = useCallback((id: string | null) => boards.find((board) => board.id === id)?.name ?? "Unsorted", [boards])

  const pins = useMemo(() => viewPins(snapshot.pins, snapshot.events), [snapshot])
  const titles = useMemo(() => new Map(pins.map((pin) => [pin.id, pin.body.title])), [pins])
  const visible = pins.filter((pin) => matches(pin, filter, boardIds) || folding.has(pin.id))
  const detail = pins.find((pin) => pin.id === detailId) ?? null


  const settle = useCallback((id: string) => {
    inFlight.current.delete(id)
    setBusy(new Set(inFlight.current))
  }, [])

  const choose = useCallback(
    async (pin: PinView, action: Action, board?: string, name?: string) => {
      if (!live || inFlight.current.has(pin.id)) return
      inFlight.current.add(pin.id)
      setBusy(new Set(inFlight.current))
      installs.current++
      setOpenId(null)
      setErrors((now) => {
        const next = new Map(now)
        next.delete(pin.id)
        return next
      })
      const changed: InboxEvent[] = []
      try {
        for (const pending of pin.history.filter((event) => event.status === "pending")) {
          if (isChangeOfMind(pending, action, board)) {
            const cancelled = await cancelChoice(pending.id)
            if (cancelled) changed.push(cancelled)
          }
        }
        const known = upsert(snapshot.events, changed)
        const key = choiceKey(pin, action, board, known)
        const payload: Record<string, string> = action === "move" && board ? { board, name: name ?? board } : {}
        const card = cards.current.get(pin.id)
        const shelf = board ? (shelves.current.get(board) ?? shelves.current.get("all") ?? null) : null
        if (action === "move" && card) flyTo(card, shelf)
        const event = await postChoice({ action, target: `pins/${pin.id}`, payload, key })
        installs.current++
        setSnapshot((now) => ({ ...now, events: upsert(now.events, [...changed, event]) }))
        if (action === "reject" && filter.kind !== "set-aside") setFolding((now) => new Set(now).add(pin.id))
      } catch (failure) {
        installs.current++
        if (changed.length) setSnapshot((now) => ({ ...now, events: upsert(now.events, changed) }))
        setErrors((now) => new Map(now).set(pin.id, failure instanceof Error ? failure.message : "That choice did not reach the page's server."))
      } finally {
        settle(pin.id)
      }
      const fresh = await loadSnapshot()
      if (fresh && inFlight.current.size === 0) {
        installs.current++
        setSnapshot(fresh)
      }
    },
    [live, snapshot.events, filter.kind, settle],
  )

  const pickFilter = useCallback((next: Filter) => {
    window.location.hash = filterHash(next)
    setFilter(next)
    setDetailId(null)
  }, [])

  const registerCard = useCallback((id: string, el: HTMLElement | null) => {
    if (el) cards.current.set(id, el)
    else cards.current.delete(id)
  }, [])
  const registerShelf = useCallback((id: string, el: HTMLElement | null) => {
    if (el) shelves.current.set(id, el)
    else shelves.current.delete(id)
  }, [])
  const onFolded = useCallback((id: string) => {
    setFolding((now) => {
      const next = new Set(now)
      next.delete(id)
      return next
    })
  }, [])

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header className="sticky top-0 z-20 border-b border-border/70 bg-background/95 px-4 pt-[max(env(safe-area-inset-top),0.875rem)] pb-3 md:px-8 md:pt-6">
        <h1 className="mb-3 font-display text-[2.5rem] leading-none text-balance md:text-6xl">
          {config.name ? `${config.name}'s boards` : "Pinboard"}
        </h1>
        <Shelves boards={boards} pins={pins} filter={filter} onFilter={pickFilter} register={registerShelf} />
      </header>
      <main className="px-2 pt-2 pb-[max(env(safe-area-inset-bottom),2rem)] md:px-8 md:pt-5">
        {mode !== "loading" && (
          <Wall
            key={filterHash(filter)}
            pins={visible}
            empty={pins.length === 0}
            filter={filter}
            ratioOf={(pin) => ratios.get(pin.body.image) ?? 0.8}
            onShowAll={() => pickFilter({ kind: "all" })}
          >
            {(pin, arrival) => (
              <PinCard
                key={`${pin.id} ${pin.body.image}`}
                pin={pin}
                boards={boards}
                boardName={boardName}
                foundFor={pin.body.found_for ? (titles.get(pin.body.found_for) ?? null) : null}
                showBoard={filter.kind !== "board"}
                live={live}
                busy={busy.has(pin.id)}
                ratio={ratios.get(pin.body.image)}
                arrival={arrival}
                folding={folding.has(pin.id)}
                open={openId === pin.id}
                error={errors.get(pin.id) ?? null}
                onOpenChoices={setOpenId}
                onDetail={setDetailId}
                onChoose={choose}
                onFolded={onFolded}
                register={registerCard}
              />
            )}
          </Wall>
        )}
      </main>
      <PinDetail
        pin={detail}
        boards={boards}
        boardName={boardName}
        live={live}
        busy={detail ? busy.has(detail.id) : false}
        onClose={() => setDetailId(null)}
        onChoose={(pin, action, board, name) => {
          setDetailId(null)
          window.setTimeout(() => choose(pin, action, board, name), 180)
        }}
        onTag={(tag) => pickFilter({ kind: "tag", tag })}
      />
    </div>
  )
}

interface WallProps {
  pins: PinView[]
  empty: boolean
  filter: Filter
  ratioOf: (pin: PinView) => number
  onShowAll: () => void
  children: (pin: PinView, arrival: number | null) => ReactNode
}

const COLUMN_WIDTHS: [number, number][] = [
  [1400, 5],
  [1100, 4],
  [768, 3],
]
const columnsNow = () => COLUMN_WIDTHS.find(([width]) => window.matchMedia(`(min-width: ${width}px)`).matches)?.[1] ?? 2

function useColumns(): number {
  const [columns, setColumns] = useState(columnsNow)
  useEffect(() => {
    const update = () => setColumns(columnsNow())
    window.addEventListener("resize", update)
    return () => window.removeEventListener("resize", update)
  }, [])
  return columns
}

/**
 * The masonry. Each card is placed once, in the shortest column or under the pin it was found for, and keeps that
 * column: when a neighbor folds away or a find arrives, only the cards below it in its own column slide. Cards new
 * to this view arrive in a short stagger; cards that stay glide to their new places.
 */
function Wall({ pins, empty, filter, ratioOf, onShowAll, children }: WallProps) {
  const wall = useRef<HTMLDivElement | null>(null)
  const seen = useRef(new Set<string>())
  const places = useRef(new Map<string, { x: number; y: number }>())
  const columns = useColumns()
  const placed = useRef({ columns, at: new Map<string, number>() })
  if (placed.current.columns !== columns) placed.current = { columns, at: new Map() }
  const order = pins.map((pin) => pin.id).join(" ")

  const lanes: PinView[][] = Array.from({ length: columns }, () => [])
  const heights: number[] = Array(columns).fill(0)
  for (const pin of pins) {
    const at = placed.current.at
    let column = at.get(pin.id)
    if (column === undefined) {
      const asker = pin.body.found_for ? at.get(pin.body.found_for) : undefined
      column = asker ?? heights.indexOf(Math.min(...heights))
      at.set(pin.id, column)
    }
    lanes[column].push(pin)
    heights[column] += 1 / ratioOf(pin) + 0.45
  }

  let fresh = 0
  const arrivals = new Map<string, number>()
  for (const pin of pins) if (!seen.current.has(pin.id)) arrivals.set(pin.id, Math.min(fresh++, 16) * 45)

  useEffect(() => {
    for (const pin of pins) seen.current.add(pin.id)
  })

  useEffect(() => {
    if (!wall.current) return
    const cards = new Map<string, HTMLElement>()
    for (const el of wall.current.querySelectorAll<HTMLElement>("[data-pin]")) cards.set(el.dataset.pin!, el)
    places.current = places.current.size === 0 ? measure(wall.current, cards) : flip(wall.current, cards, places.current)
  }, [order, columns])

  if (pins.length === 0) {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center">
        <p className="font-display text-3xl">{empty ? "No pins yet." : filter.kind === "set-aside" ? "Nothing set aside." : "Nothing here yet."}</p>
        <p className="text-base text-pretty text-muted-foreground">
          {empty
            ? "Ask your agent to find a few things for a board, and they land here."
            : filter.kind === "set-aside"
              ? "Pins you set aside wait here, out of the way."
              : "Move a pin here from Everything, or ask your agent for more."}
        </p>
        {!empty && (
          <Button variant="outline" onClick={onShowAll}>
            Show everything
          </Button>
        )}
      </div>
    )
  }

  return (
    <div ref={wall} className="wall relative">
      {lanes.map((lane, column) => (
        <div key={column} className="wall-column">
          {lane.map((pin) => (
            <div key={pin.id} data-pin={pin.id}>
              {children(pin, arrivals.get(pin.id) ?? null)}
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}
