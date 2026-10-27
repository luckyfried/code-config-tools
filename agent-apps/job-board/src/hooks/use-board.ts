import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { cancelChoice, isLive, loadInbox, loadRecords, sendChoice } from "@/lib/api"
import { buildCards, choiceKey, KIND, sampleEvents, sampleRecords, STATUS_ACTIONS, supersedes, target } from "@/lib/board"
import { abort, flip, launch, reduced, snapshot, type Flight } from "@/lib/motion"
import type { Action, AppConfig, Card, InboxEvent, StoredRecord } from "@/types"

export type Mode = "loading" | "live" | "sample"
const POLL_MS = 5000

// The sample tour: with no runtime behind the page, the board shows once what each of the three moves and the agent
// sending an application look like, starting after the board has settled. Every move takes the top of the pile.
const top = (c: Card[]) => c.find((x) => x.shown === "new")
const TOUR: { at: number; run: "finish" | Exclude<Action, "apply">; pick: (cards: Card[]) => Card | undefined }[] = [
  { at: 3300, run: "yes", pick: top },
  { at: 4400, run: "yes", pick: top },
  { at: 5500, run: "finish", pick: (c) => c.find((x) => x.latest?.status === "working") },
  { at: 6500, run: "later", pick: top },
  { at: 7600, run: "no", pick: top },
]

// A yes, no, or later lifts the card off where it was; it flies once the board has moved it.
const lift = (card: Card, action: Action, fromX = 0) =>
  STATUS_ACTIONS.includes(action) ? launch(card.record.id, action, fromX) : null

export function useBoard(config: AppConfig) {
  const [mode, setMode] = useState<Mode>("loading")
  const [records, setRecords] = useState<StoredRecord[]>([])
  const [events, setEvents] = useState<InboxEvent[]>([])
  const [viewOnly, setViewOnly] = useState<string | null>(null)
  const [cardProblem, setCardProblem] = useState<Record<string, string>>({})
  // One choice in flight per card: from the tap until its server calls settle, the card takes no other choice.
  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const busyRef = useRef(busy)
  const pendingFlip = useRef<{ before: Map<string, DOMRect>; moved: string | null; flight: Flight | null } | null>(null)
  const eventsRef = useRef(events)
  const cards = useMemo(() => buildCards(records, events), [records, events])
  const cardsRef = useRef(cards)
  useLayoutEffect(() => {
    eventsRef.current = events
    cardsRef.current = cards
  }, [events, cards])

  const refresh = useCallback(async (moved: string | null = null, flight: Flight | null = null) => {
    try {
      const [r, e] = await Promise.all([loadRecords(KIND), loadInbox()])
      pendingFlip.current = { before: snapshot(), moved, flight }
      setRecords(r)
      setEvents(e)
    } catch {
      // A missed read is retried on the next poll; a choice that cannot be sent says so on its card.
      if (moved) abort(flight, moved)
    }
  }, [])

  useEffect(() => {
    let stop = false
    let timer = 0
    void isLive().then(async (live) => {
      if (stop) return
      if (!live) {
        setRecords(sampleRecords(config))
        setEvents(sampleEvents(config))
        setMode("sample")
        return
      }
      setMode("live")
      await refresh()
      timer = window.setInterval(() => {
        if (document.visibilityState === "visible") void refresh()
      }, POLL_MS)
    })
    return () => {
      stop = true
      window.clearInterval(timer)
    }
  }, [config, refresh])

  useLayoutEffect(() => {
    const f = pendingFlip.current
    if (!f) return
    pendingFlip.current = null
    flip(f.before, f.moved, f.flight)
  })


  const choose = useCallback(
    async (card: Card, action: Action, fromX = 0) => {
      const id = card.record.id
      if (mode === "sample") setViewOnly(id)
      if (mode !== "live" || busyRef.current[id]) return
      if (STATUS_ACTIONS.includes(action) && card.shown === action) return
      const key = choiceKey(card, action, eventsRef.current)
      if (eventsRef.current.some((e) => e.key === key)) return
      busyRef.current = { ...busyRef.current, [id]: true }
      setBusy(busyRef.current)
      setCardProblem(({ [id]: _gone, ...rest }) => rest)
      try {
        // A changed mind cancels the earlier pending choice first; one the agent is already working on stays.
        const t = target(id)
        for (const e of eventsRef.current.filter((x) => x.target === t && supersedes(x, action))) await cancelChoice(e.id)
        await sendChoice(action, t, key)
        await refresh(id, lift(card, action, fromX))
      } catch (err) {
        abort(null, id)
        setCardProblem((p) => ({ ...p, [id]: err instanceof Error ? err.message : String(err) }))
      } finally {
        busyRef.current = { ...busyRef.current, [id]: false }
        setBusy(busyRef.current)
      }
    },
    [mode, refresh],
  )

  // The tour plays once, in sample mode only, and never under reduced motion. It moves the sample's own records.
  useEffect(() => {
    if (mode !== "sample" || reduced()) return
    const timers = TOUR.map((step) =>
      window.setTimeout(async () => {
        const card = step.pick(cardsRef.current)
        if (!card) return
        if (step.run === "finish") {
          const done = new Date().toISOString()
          setEvents((list) =>
            list.map((e) =>
              e.id === card.latest!.id
                ? { ...e, status: "completed", result: { next: "ask the person, then act", done_at: done } }
                : e,
            ),
          )
          setRecords((list) =>
            list.map((r) => (r.id === card.record.id ? { ...r, body: { ...r.body, applied_at: done } } : r)),
          )
          return
        }
        const status = step.run
        const flight = lift(card, status)
        pendingFlip.current = { before: snapshot(), moved: card.record.id, flight }
        const at = new Date().toISOString()
        setRecords((list) =>
          list.map((r) => (r.id === card.record.id ? { ...r, revision: r.revision + 1, at, body: { ...r.body, status } } : r)),
        )
      }, step.at),
    )
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [mode])

  return { mode, cards, events, cardProblem, busy, viewOnly, choose }
}
