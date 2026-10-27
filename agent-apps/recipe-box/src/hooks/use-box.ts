import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { cancelChoice, isLive, loadInbox, loadRecords, sendChoice } from "@/lib/api"
import {
  choiceKey,
  LISTS,
  latestByTarget,
  type ListRecord,
  newestList,
  open,
  planKey,
  RECIPES,
  type RecipeRecord,
  sampleEvents,
  sampleLists,
  sampleRecipes,
  shownState,
  target,
} from "@/lib/box"
import { COPY } from "@/lib/copy"
import { flyToSlot, foldAway, nod, reduced } from "@/lib/motion"
import { readLocal, writeLocal, type Filter, type Local } from "@/lib/store"
import type { Action, AppConfig, Day, InboxEvent, Recipe, ShoppingList, Status } from "@/types"

export type Mode = "loading" | "live" | "sample"
type Shown = { status: Status; day: Day | null }
const POLL_MS = 5000

export interface Item {
  record: RecipeRecord
  shown: Shown
  latest: InboxEvent | undefined
}

// Image sizes are read before the box first draws, so each card lands at its own shape and nothing jumps.
function preload(srcs: string[], capMs: number): Promise<Record<string, number | "failed">> {
  const out: Record<string, number | "failed"> = {}
  return new Promise((done) => {
    let left = srcs.length
    const timer = window.setTimeout(() => done({ ...out }), capMs)
    if (!left) {
      window.clearTimeout(timer)
      done(out)
      return
    }
    for (const src of srcs) {
      const img = new Image()
      const settle = (v: number | "failed") => {
        out[src] = v
        if (--left === 0) {
          window.clearTimeout(timer)
          done({ ...out })
        }
      }
      img.onload = () => settle(img.naturalWidth && img.naturalHeight ? img.naturalWidth / img.naturalHeight : 0.8)
      img.onerror = () => settle("failed")
      img.src = src
    }
  })
}

export function useBox(config: AppConfig) {
  const [mode, setMode] = useState<Mode>("loading")
  const [recipes, setRecipes] = useState<RecipeRecord[]>([])
  const [lists, setLists] = useState<ListRecord[]>([])
  const [events, setEvents] = useState<InboxEvent[]>([])
  const [ratios, setRatios] = useState<Record<string, number | "failed">>({})
  const [ready, setReady] = useState(false)
  const [overrides, setOverrides] = useState<Record<string, Shown>>({})
  const [introGlow, setIntroGlow] = useState(false)
  const [receipt, setReceipt] = useState<string | null>(null)
  const [demoTicks, setDemoTicks] = useState<string[]>([])
  const [local, setLocal] = useState<Local>(readLocal)
  const [problem, setProblem] = useState<Record<string, string>>({})
  const [stripNote, setStripNote] = useState<string | null>(null)
  const busy = useRef<Record<string, boolean>>({})
  const seenOpenPlans = useRef(new Set<string>())

  const latest = useMemo(() => latestByTarget(events), [events])
  const items: Item[] = useMemo(
    () =>
      [...recipes]
        .sort((a, b) => (a.body.found_at < b.body.found_at ? 1 : a.body.found_at > b.body.found_at ? -1 : a.id.localeCompare(b.id)))
        .map((record) => {
          const o = overrides[record.id]
          const l = latest.get(target(record.id))
          return { record, shown: o ?? shownState(record, l), latest: o ? undefined : l }
        }),
    [recipes, latest, overrides],
  )
  const itemsRef = useRef(items)
  const eventsRef = useRef(events)
  useEffect(() => {
    itemsRef.current = items
    eventsRef.current = events
  }, [items, events])

  const planEvent = useMemo(() => [...events].reverse().find((e) => e.action === "plan-week"), [events])
  const glow = introGlow || open(planEvent)

  const updateLocal = useCallback((change: (l: Local) => Local) => {
    setLocal((l) => {
      const next = change(l)
      writeLocal(next)
      return next
    })
  }, [])

  const ratiosRef = useRef(ratios)
  useEffect(() => {
    ratiosRef.current = ratios
  }, [ratios])

  const refresh = useCallback(async () => {
    try {
      const [r, l, e] = await Promise.all([loadRecords<Recipe>(RECIPES), loadRecords<ShoppingList>(LISTS), loadInbox()])
      const missing = r.map((x) => x.body.image).filter((src) => src && !(src in ratiosRef.current))
      if (missing.length) {
        const found = await preload([...new Set(missing)], 1500)
        setRatios((old) => ({ ...old, ...found }))
      }
      setRecipes(r)
      setLists(l)
      setEvents(e)
    } catch {
      // A missed read is tried again on the next poll; a choice that cannot be sent says so on its card.
    }
  }, [])
  useEffect(() => {
    let stop = false
    let timer = 0
    void isLive().then(async (live) => {
      if (stop) return
      if (!live) {
        const r = sampleRecipes(config)
        const found = await preload([...new Set(r.map((x) => x.body.image))], 1200)
        if (stop) return
        setRatios(found)
        if (!reduced()) {
          const start: Record<string, Shown> = {}
          for (const x of r) if (x.body.status !== "new") start[x.id] = { status: "new", day: null }
          setOverrides(start)
        }
        setRecipes(r)
        setLists(sampleLists(config))
        setEvents(sampleEvents(config))
        setMode("sample")
        setReady(true)
        return
      }
      setMode("live")
      await refresh()
      if (stop) return
      setReady(true)
      timer = window.setInterval(() => {
        if (document.visibilityState === "visible") void refresh()
      }, POLL_MS)
    })
    return () => {
      stop = true
      window.clearInterval(timer)
    }
  }, [config, refresh])

  // The sample plays the week being made once: picks arc into their days, keeps nod, a skip folds away, the strip
  // glows while the agent works, and the list prints.
  useEffect(() => {
    if (mode !== "sample" || reduced()) return
    const r = sampleRecipes(config)
    const clear = (id: string) =>
      setOverrides(({ [id]: _gone, ...rest }) => rest)
    const order: Day[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    const week = r.filter((x) => x.body.status === "week").sort((a, b) => order.indexOf(a.body.day!) - order.indexOf(b.body.day!))
    const kept = r.filter((x) => x.body.status === "kept")
    const skipped = r.filter((x) => x.body.status === "skipped")
    const timers: number[] = []
    const at = (ms: number, run: () => void) => timers.push(window.setTimeout(run, ms))
    week.forEach((x, n) =>
      at(620 + n * 170, () => {
        void flyToSlot(x.id, x.body.day!, x.body.image, x.body.color).then(() => clear(x.id))
      }),
    )
    kept.forEach((x, n) =>
      at(1150 + n * 160, () => {
        clear(x.id)
        nod(x.id)
      }),
    )
    skipped.forEach((x, n) =>
      at(1350 + n * 160, () => {
        void foldAway(x.id).then(() => clear(x.id))
      }),
    )
    // The box settles first and rests with "Plan the week" showing; the plan runs once after that.
    at(3300, () => setIntroGlow(true))
    at(4200, () => {
      setIntroGlow(false)
      const list = newestList(sampleLists(config))
      if (list) setReceipt(list.id)
    })
    const first = newestList(sampleLists(config))?.body.items ?? []
    first.slice(0, 3).forEach((it, n) => at(5700 + n * 650, () => setDemoTicks((t) => [...t, it.name + "|" + (it.unit ?? "")])))
    return () => timers.forEach((t) => window.clearTimeout(t))
  }, [mode, config])

  // A plan the person asked for opens its list when the agent finishes it.
  useEffect(() => {
    if (mode !== "live") return
    for (const e of events) {
      if (e.action !== "plan-week") continue
      if (open(e)) seenOpenPlans.current.add(e.id)
      else if (seenOpenPlans.current.has(e.id)) {
        seenOpenPlans.current.delete(e.id)
        if (e.status === "completed" && e.result?.list) setReceipt(e.result.list)
      }
    }
  }, [events, mode])

  const addEvent = (event: InboxEvent, cancelled: string[] = []) =>
    setEvents((list) => [
      ...list.filter((e) => e.id !== event.id).map((e) => (cancelled.includes(e.id) ? { ...e, status: "cancelled" as const } : e)),
      event,
    ])

  const choose = useCallback(
    async (record: RecipeRecord, action: Exclude<Action, "plan-week">, day?: Day, dropped = false) => {
      if (mode !== "live" || busy.current[record.id]) return
      const item = itemsRef.current.find((x) => x.record.id === record.id)
      if (!item) return
      const status: Status = action === "keep" ? "kept" : action === "skip" ? "skipped" : "week"
      if (action === "week" && !day) return
      if (item.shown.status === status && (action !== "week" || item.shown.day === day)) return
      busy.current[record.id] = true
      setProblem(({ [record.id]: _gone, ...rest }) => rest)
      try {
        if (action === "keep") nod(record.id)
        if (action === "skip") await foldAway(record.id)
        if (action === "week" && !dropped) await flyToSlot(record.id, day!, record.body.image, record.body.color)
        // A changed mind cancels the earlier pending choice first; one the agent is already working on stays.
        const cancelled: string[] = []
        const prior = item.latest
        if (prior && prior.status === "pending") {
          if (await cancelChoice(prior.id)) cancelled.push(prior.id)
        }
        const event = await sendChoice(action, target(record.id), choiceKey(record, action), day)
        addEvent(event, cancelled)
        void refresh()
      } catch (err) {
        setProblem((p) => ({ ...p, [record.id]: err instanceof Error ? err.message : String(err) }))
      } finally {
        busy.current[record.id] = false
        window.setTimeout(() => cardAnimationsDone(record.id), 60)
      }
    },
    [mode, refresh],
  )

  const planWeek = useCallback(async () => {
    if (mode !== "live") return
    const ids = itemsRef.current.filter((x) => x.shown.status === "week").map((x) => x.record.id)
    if (!ids.length) {
      setStripNote(COPY.pickFirst)
      return
    }
    setStripNote(null)
    try {
      const event = await sendChoice("plan-week", null, planKey(ids))
      seenOpenPlans.current.add(event.id)
      addEvent(event)
      if (event.status === "completed" && event.result?.list) setReceipt(event.result.list)
      void refresh()
    } catch (err) {
      setStripNote(err instanceof Error ? err.message : String(err))
    }
  }, [mode, refresh])

  const setFilter = (filter: Filter) => updateLocal((l) => ({ ...l, filter }))
  const toggleTick = (listId: string, line: string) =>
    updateLocal((l) => {
      const now = l.ticked[listId] ?? []
      const next = now.includes(line) ? now.filter((x) => x !== line) : [...now, line]
      return { ...l, ticked: { ...l.ticked, [listId]: next } }
    })

  const receiptList = receipt ? lists.find((l) => l.id === receipt) ?? null : null
  const ticked = receiptList ? [...(local.ticked[receiptList.id] ?? []), ...(mode === "sample" ? demoTicks : [])] : []

  return {
    mode,
    ready,
    items,
    lists,
    events,
    ratios,
    setRatio: (src: string, v: number | "failed") => setRatios((r) => (r[src] === v ? r : { ...r, [src]: v })),
    glow,
    planEvent,
    receiptList,
    openReceipt: (id: string | null) => setReceipt(id),
    ticked,
    toggleTick,
    filter: local.filter,
    setFilter,
    problem,
    stripNote,
    choose,
    planWeek,
  }
}

// A folded card that stays in view (under the "Skipped" filter) stands back up.
function cardAnimationsDone(id: string) {
  const el = document.querySelector<HTMLElement>(`[data-card="${CSS.escape(id)}"]`)
  el?.getAnimations().forEach((a) => {
    if (a.playState === "finished") a.cancel()
  })
}
