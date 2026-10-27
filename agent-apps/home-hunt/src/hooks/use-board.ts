import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { cancelChoice, isLive, loadInbox, loadRecords, sendChoice } from "@/lib/api"
import { buildCards, KIND, newId, replaced, sampleEvents, sampleRecords, statusKey, STATUS_ACTIONS, target } from "@/lib/board"
import { flip, leaveList, pressSeal, slideOut, snapshot, tipCard } from "@/lib/motion"
import type { Action, AppConfig, Card, InboxEvent, StoredRecord } from "@/types"

export type Mode = "loading" | "live" | "sample"
const POLL_MS = 5000

export function useBoard(config: AppConfig, phone: boolean) {
  const [mode, setMode] = useState<Mode>("loading")
  const [records, setRecords] = useState<StoredRecord[]>([])
  const [events, setEvents] = useState<InboxEvent[]>([])
  const [problem, setProblem] = useState<Record<string, string>>({})
  // One choice in flight per card: from the tap until its server calls settle, the card takes no other choice.
  const busyRef = useRef<Record<string, boolean>>({})
  const [, setBusyTick] = useState(0)
  const pendingFlip = useRef<{ before: Map<string, DOMRect>; moved: string | null; how: "yes" | "maybe" | null } | null>(null)
  const cards = useMemo(() => buildCards(records, events), [records, events])
  const cardsRef = useRef(cards)
  const eventsRef = useRef(events)
  useLayoutEffect(() => {
    cardsRef.current = cards
    eventsRef.current = events
  }, [cards, events])

  const refresh = useCallback(async (moved: string | null = null, how: "yes" | "maybe" | null = null) => {
    try {
      const [r, e] = await Promise.all([loadRecords(KIND), loadInbox()])
      pendingFlip.current = { before: snapshot(), moved, how }
      setRecords(r)
      setEvents(e)
    } catch {
      // A missed read is retried on the next poll; a choice that cannot be sent says so on its card.
    }
  }, [])

  useEffect(() => {
    let stop = false
    let timer = 0
    void isLive().then(async (isOn) => {
      if (stop) return
      if (!isOn) {
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
    flip(f.before, f.moved, f.how)
  })

  // The card's exit from where it was: on a phone it leaves the list; on a desktop yes presses a seal, no slides
  // out to the left, and maybe tips toward the pile.
  const exit = useCallback(
    (id: string, action: Action, from = { x: 0, y: 0 }): Promise<void> => {
      if (!STATUS_ACTIONS.includes(action)) return Promise.resolve()
      if (phone) return leaveList(id, action, from)
      if (action === "yes") return pressSeal(id)
      if (action === "no") return slideOut(id)
      return tipCard(id)
    },
    [phone],
  )

  const setBusy = (id: string, on: boolean) => {
    busyRef.current = { ...busyRef.current, [id]: on }
    setBusyTick((n) => n + 1)
  }

  const send = useCallback(
    async (card: Card, action: Action, payload: Record<string, unknown>, key: string, from?: { x: number; y: number }) => {
      const id = card.id
      if (mode !== "live" || busyRef.current[id]) return false
      setBusy(id, true)
      setProblem(({ [id]: _gone, ...rest }) => rest)
      try {
        // A changed mind cancels the earlier pending choice first; one the agent is already working on stays.
        if (STATUS_ACTIONS.includes(action)) for (const e of replaced(card, action)) await cancelChoice(e.id)
        await sendChoice(action, target(id), payload, key)
        await exit(id, action, from)
        await refresh(id, action === "yes" || action === "maybe" ? action : null)
        return true
      } catch (err) {
        setProblem((p) => ({ ...p, [id]: err instanceof Error ? err.message : String(err) }))
        return false
      } finally {
        setBusy(id, false)
      }
    },
    [mode, exit, refresh],
  )

  const choose = useCallback(
    (card: Card, action: Action, from?: { x: number; y: number }) => {
      if (mode === "live" && card.shown === action) return Promise.resolve(false)
      return send(card, action, {}, statusKey(card, action), from)
    },
    [mode, send],
  )

  const note = useCallback(
    (card: Card, text: string) => send(card, "note", { text: text.slice(0, 2000) }, `${target(card.id)}:note:${newId()}`),
    [send],
  )

  const ask = useCallback(
    (card: Card, question: string) =>
      send(card, "ask", { question: question.slice(0, 2000) }, `${target(card.id)}:ask:${newId()}`),
    [send],
  )

  // The sample tour moves the sample's own homes in memory: a choice shows as waiting for the agent, as a real one
  // would, and an answer lands on a question.
  const demoMove = useCallback(
    async (card: Card, action: "yes" | "no" | "maybe") => {
      await exit(card.id, action)
      pendingFlip.current = { before: snapshot(), moved: card.id, how: action === "no" ? null : action }
      const at = new Date().toISOString()
      setEvents((list) => [
        ...list,
        {
          id: `tour-${card.id}-${action}`,
          action,
          target: target(card.id),
          key: statusKey(card, action),
          at,
          payload: {},
          status: "pending",
          result: null,
          error: null,
        },
      ])
    },
    [exit],
  )

  const demoAnswer = useCallback((id: string, answer: string) => {
    const at = new Date().toISOString()
    setRecords((list) =>
      list.map((r) =>
        r.id !== id
          ? r
          : {
              ...r,
              revision: r.revision + 1,
              body: {
                ...r.body,
                questions: r.body.questions.map((q) => (q.answer == null ? { ...q, answer, answered_at: at } : q)),
              },
            },
      ),
    )
  }, [])

  return {
    mode,
    cards,
    cardsRef,
    events,
    problem,
    busy: busyRef.current,
    choose,
    note,
    ask,
    demoMove,
    demoAnswer,
  }
}
