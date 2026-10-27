import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { cancelChoice, isLive, loadInbox, loadRecords, sendChoice } from "@/lib/api"
import type { Action, AppConfig, Article, Deep, InboxEvent, Topic } from "@/types"

export type Mode = "loading" | "sample" | "live"

const POLL_MS = 5000

export const config: AppConfig = window.__APP_CONFIG__ ?? { name: "", topics: [] }

/** The article id an event points at; the runtime names its target "articles/<id>". */
export const targetId = (target: string) => target.slice(target.indexOf("/") + 1)

const sampleArticles = (): Article[] => (config.sample?.articles ?? []).map((a) => ({ ...a, revision: 1 }))
const sampleEvents = (): InboxEvent[] => (config.sample?.inbox ?? []).map((e) => ({ ...e }))

const byTime = (a: InboxEvent, b: InboxEvent) => a.at.localeCompare(b.at)

/** Every event on each article, oldest first. */
function eventsByArticle(events: InboxEvent[]) {
  const map = new Map<string, InboxEvent[]>()
  for (const e of [...events].sort(byTime)) {
    const id = targetId(e.target ?? "")
    map.set(id, [...(map.get(id) ?? []), e])
  }
  return map
}

const PLACING: Action[] = ["later", "skip"]
const standing = (e: InboxEvent) => e.status !== "cancelled" && e.status !== "failed"

/** Where the person put a story: the latest standing later or skip on it, else what its record says. */
export function placeOf(a: Article, history: InboxEvent[] | undefined): Article["status"] {
  const choice = [...(history ?? [])].reverse().find((e) => PLACING.includes(e.action) && standing(e))
  if (!choice) return a.status
  return choice.action === "later" ? "later" : "skipped"
}

export function usePaper() {
  const [mode, setMode] = useState<Mode>("loading")
  const [articles, setArticles] = useState<Article[]>([])
  const [storedTopics, setStoredTopics] = useState<Topic[]>([])
  const [events, setEvents] = useState<InboxEvent[]>([])
  const [opening, setOpening] = useState<Set<string>>(new Set())
  const [notice, setNotice] = useState<string | null>(null)
  const briefed = useRef<Set<string> | null>(null)

  // A story whose brief has just landed opens into a long read once.
  useEffect(() => {
    if (mode === "loading") return
    const now = new Set(articles.filter((a) => a.deep).map((a) => a.id))
    const before = briefed.current
    briefed.current = now
    if (!before) return
    const fresh = [...now].filter((id) => !before.has(id))
    if (!fresh.length) return
    setOpening((s) => new Set([...s, ...fresh]))
    window.setTimeout(() => setOpening((s) => new Set([...s].filter((id) => !fresh.includes(id)))), 1600)
  }, [articles, mode])

  const refresh = useCallback(async () => {
    try {
      const [rows, topicRows, inbox] = await Promise.all([
        loadRecords<Omit<Article, "revision">>("articles"),
        loadRecords<Topic>("topics"),
        loadInbox(),
      ])
      setArticles(rows.map((r) => ({ ...r.body, id: r.id, revision: r.revision })))
      setStoredTopics(topicRows.map((r) => r.body))
      setEvents(inbox)
    } catch (e) {
      setNotice((e as Error).message)
    }
  }, [])

  useEffect(() => {
    let stop = false
    let timer = 0
    isLive().then(async (live) => {
      if (stop) return
      if (!live) {
        setArticles(sampleArticles())
        setEvents(sampleEvents())
        setMode("sample")
        return
      }
      await refresh()
      if (stop) return
      setMode("live")
      timer = window.setInterval(() => {
        if (!document.hidden) refresh()
      }, POLL_MS)
    })
    return () => {
      stop = true
      window.clearInterval(timer)
    }
  }, [refresh])

  const topics = storedTopics.length ? storedTopics : config.topics
  const history = useMemo(() => eventsByArticle(events), [events])

  const lastChecked = useMemo(() => {
    const done = events.filter((e) => e.status === "completed").sort(byTime)
    return done.length ? done[done.length - 1].at : null
  }, [events])

  const merge = useCallback((e: InboxEvent) => {
    setEvents((list) => [...list.filter((x) => x.id !== e.id), e])
  }, [])

  /** Sends one choice; a later or skip that changes a pending one cancels that one first. */
  const choose = useCallback(
    async (action: Action, a: Article): Promise<boolean> => {
      if (mode !== "live") return false
      setNotice(null)
      try {
        if (PLACING.includes(action)) {
          const pending = (history.get(a.id) ?? []).filter(
            (e) => PLACING.includes(e.action) && e.action !== action && e.status === "pending",
          )
          for (const e of pending) {
            const gone = await cancelChoice(e.id)
            if (gone) merge(gone)
          }
        }
        const target = `articles/${a.id}`
        merge(await sendChoice(action, target, `${target}:${action}:${a.revision}`))
        return true
      } catch (e) {
        setNotice((e as Error).message)
        return false
      }
    },
    [mode, history, merge],
  )

  /** Takes back a choice the agent has not picked up yet. */
  const takeBack = useCallback(
    async (e: InboxEvent) => {
      if (mode === "sample") {
        merge({ ...e, status: "cancelled" })
        return
      }
      const gone = await cancelChoice(e.id)
      if (gone) merge(gone)
      else setNotice("The agent has already taken this choice.")
    },
    [mode, merge],
  )

  /** The sample's own playback: a choice made on the page as it would be in the person's project. */
  const play = useCallback(
    (action: Action, a: Article) => {
      const e: InboxEvent = {
        id: `sample-${action}-${a.id}`,
        action,
        target: `articles/${a.id}`,
        status: "pending",
        at: new Date().toISOString(),
        result: null,
      }
      merge(e)
      return e
    },
    [merge],
  )

  const playTaken = useCallback(
    (e: InboxEvent, result: Record<string, unknown>) => merge({ ...e, status: "completed", result, at: new Date().toISOString() }),
    [merge],
  )

  const playBrief = useCallback(
    (id: string, deep: Deep) => {
      setArticles((list) => list.map((a) => (a.id === id ? { ...a, deep } : a)))
      setEvents((list) =>
        list.map((e) =>
          targetId(e.target) === id && e.action === "deeper" && e.status === "pending"
            ? { ...e, status: "completed", result: { next: "write a longer brief on this article" } }
            : e,
        ),
      )
    },
    [],
  )

  return {
    mode,
    articles,
    topics,
    events,
    history,
    opening,
    lastChecked,
    notice,
    setNotice,
    choose,
    takeBack,
    play,
    playTaken,
    playBrief,
  }
}

export type Paper = ReturnType<typeof usePaper>
