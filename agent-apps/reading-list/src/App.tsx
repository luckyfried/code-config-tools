import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type CSSProperties } from "react"
import { config, placeOf, usePaper } from "@/hooks/use-paper"
import { useColumns } from "@/hooks/use-media"
import { useImageSizes } from "@/hooks/use-image-sizes"
import { askShape, drawnShape, pack } from "@/lib/pack"
import { fadeToNewsprint, foldIntoStack, reducedMotion, reflow, ripple, snapshot, type Snapshot } from "@/lib/motion"
import type { Action, Article, Topic } from "@/types"
import { DuotoneFilters } from "@/components/duotone"
import { HoldSheet } from "@/components/hold-sheet"
import { LaterSheet, StackButton } from "@/components/later-stack"
import { Masthead } from "@/components/masthead"
import { StoryCard } from "@/components/story-card"
import { StoryPage } from "@/components/story-page"
import { when } from "@/lib/words"

const PREFS = "reading-list"

function readSection(): string {
  try {
    return (JSON.parse(localStorage.getItem(PREFS) ?? "{}") as { section?: string }).section ?? "all"
  } catch {
    return "all"
  }
}

const newestFirst = (a: Article, b: Article) => b.published_at.localeCompare(a.published_at)

// The sample page plays one round of choices on its own, so the page shows what each choice does before anyone
// serves it: read later, skip, more like this, and a brief landing.
const TOUR: { at: number; action: Action | "land" }[] = [
  { at: 1700, action: "later" },
  { at: 3000, action: "skip" },
  { at: 4300, action: "more" },
  { at: 6000, action: "land" },
]

export default function App() {
  const paper = usePaper()
  const cols = useColumns()
  const phone = cols === 1
  // A phone packs two narrow columns under the lead, so small stories pair up and the page stays a front page.
  const across = phone ? 2 : cols
  const live = paper.mode === "live"
  const grid = useRef<HTMLDivElement>(null)
  const stack = useRef<HTMLButtonElement>(null)
  const flip = useRef<Snapshot | null>(null)
  const [section, setSection] = useState(readSection)
  const [flying, setFlying] = useState(0)
  const [openId, setOpenId] = useState<string | null>(null)
  const [holdId, setHoldId] = useState<string | null>(null)
  const [laterOpen, setLaterOpen] = useState(false)
  const [tour, setTour] = useState<{ id: string; action: Action } | null>(null)
  const [entering, setEntering] = useState(true)
  const { sizes, ready } = useImageSizes(paper.articles)

  useEffect(() => {
    try {
      localStorage.setItem(PREFS, JSON.stringify({ section }))
    } catch {
      // A browser that keeps nothing still shows the page; the section resets on the next visit.
    }
  }, [section])

  const topics = useMemo(() => {
    const map = new Map<string, Topic>(paper.topics.map((t) => [t.id, t]))
    for (const a of paper.articles) if (!map.has(a.topic)) map.set(a.topic, { id: a.topic, name: a.topic, color: a.color })
    return map
  }, [paper.topics, paper.articles])

  const byPlace = useMemo(() => {
    const groups = { new: [] as Article[], later: [] as Article[], skipped: [] as Article[] }
    for (const a of [...paper.articles].sort(newestFirst)) groups[placeOf(a, paper.history.get(a.id))].push(a)
    return groups
  }, [paper.articles, paper.history])

  const counts = useMemo(() => {
    const m = new Map<string, number>()
    for (const a of byPlace.new) m.set(a.topic, (m.get(a.topic) ?? 0) + 1)
    return m
  }, [byPlace])

  const shown = section === "all" || topics.has(section) ? section : "all"
  const front = useMemo(() => byPlace.new.filter((a) => shown === "all" || a.topic === shown), [byPlace, shown])

  // The lead is the newest story without a brief; long reads come next, newest brief first; then the rest by date.
  // A phone sets two one-column stories side by side right under the lead, so its first screen reads as a front page.
  const layout = useMemo(() => {
    const ratio = (a: Article) => {
      const s = sizes.get(a.image)
      return s ? s.w / s.h : 1.5
    }
    const lead = front.find((a) => !a.deep) ?? front[0]
    const long = front.filter((a) => a !== lead && a.deep).sort((a, b) => b.deep!.at.localeCompare(a.deep!.at))
    const rest = front.filter((a) => a !== lead && !a.deep)
    const pair = phone ? rest.filter((a) => ["small", "tall"].includes(askShape(a, ratio(a), false))).slice(0, 2) : []
    const order = lead ? [lead, ...pair, ...long, ...rest.filter((a) => !pair.includes(a))] : []
    const items = order.map((a) => ({ id: a.id, shape: askShape(a, ratio(a), a === lead) }))
    const places = pack(items, across)
    const rank = new Map(order.map((a, i) => [a.id, i]))
    return { places, rank }
  }, [front, sizes, across, phone])

  const layoutKey = useMemo(
    () => [...layout.places].map(([id, p]) => `${id}:${p.c},${p.r},${p.cs},${p.rs}`).join("|") + `#${across}`,
    [layout, across],
  )

  useLayoutEffect(() => {
    if (flip.current) {
      reflow(grid.current, flip.current)
      flip.current = null
    }
  }, [layoutKey])

  useEffect(() => {
    if (!ready) return
    const t = window.setTimeout(() => setEntering(false), 3000)
    return () => window.clearTimeout(t)
  }, [ready])

  const act = useCallback(
    async (action: Action, a: Article, el: HTMLElement | null, played = false) => {
      if (!live && !played) return
      const send = async () => {
        if (played) {
          const e = paper.play(action, a)
          if (action === "more") window.setTimeout(() => paper.playTaken(e, { next: "find more like this article" }), 1500)
          return true
        }
        return paper.choose(action, a)
      }
      if (action === "later") {
        if (el) {
          setFlying((n) => n + 1)
          foldIntoStack(el, stack.current).finally(() => setFlying((n) => Math.max(0, n - 1)))
        }
        flip.current = snapshot(grid.current)
        if (!(await send())) setFlying((n) => Math.max(0, n - 1))
      } else if (action === "skip") {
        if (el) fadeToNewsprint(el)
        flip.current = snapshot(grid.current)
        await send()
      } else {
        if (action === "more" && el) ripple(el, topics.get(a.topic)?.color ?? a.color)
        await send()
      }
    },
    [live, paper, topics],
  )

  // The sample page's own round of choices, acted on stories in view.
  useEffect(() => {
    if (paper.mode !== "sample" || !ready || reducedMotion()) return
    const landing = config.sample?.landing
    const used = new Set<string>(landing ? [landing.id] : [])
    const pick = () => {
      const seen = [...(grid.current?.querySelectorAll<HTMLElement>("[data-story]") ?? [])]
        .filter((el) => !["lead", "long"].includes(el.dataset.shape ?? "") && !used.has(el.dataset.story!))
        .map((el) => ({ el, r: el.getBoundingClientRect() }))
        .filter(({ r }) => r.top < window.innerHeight - 160 && r.bottom > 0)
        .sort((x, y) => x.r.top - y.r.top || x.r.left - y.r.left)
      return seen[0]?.el ?? null
    }
    const timers = TOUR.map(({ at, action }) =>
      window.setTimeout(() => {
        if (action === "land") {
          if (!landing) return
          flip.current = snapshot(grid.current)
          paper.playBrief(landing.id, landing.deep)
          return
        }
        const el = pick()
        const a = el && paper.articles.find((x) => x.id === el.dataset.story)
        if (!el || !a) return
        used.add(a.id)
        setTour({ id: a.id, action })
        window.setTimeout(() => {
          setTour(null)
          act(action, a, el, true)
        }, 620)
      }, at),
    )
    return () => timers.forEach((t) => window.clearTimeout(t))
    // The round plays once, when the sample first lays out.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paper.mode, ready])

  const openArticle = paper.articles.find((a) => a.id === openId) ?? null
  const holdArticle = paper.articles.find((a) => a.id === holdId) ?? null
  const topicOf = (a: Article): Topic => topics.get(a.topic) ?? { id: a.topic, name: a.topic, color: a.color }
  const byId = useMemo(() => new Map(paper.articles.map((a) => [a.id, a])), [paper.articles])

  const choose = (action: Action, a: Article) => {
    const el = grid.current?.querySelector<HTMLElement>(`[data-story="${CSS.escape(a.id)}"]`) ?? null
    setOpenId(null)
    setHoldId(null)
    window.setTimeout(() => act(action, a, el), el && (action === "later" || action === "skip") ? 260 : 0)
  }

  const sectionName = shown === "all" ? null : topics.get(shown)?.name

  return (
    <div className="paper">
      <DuotoneFilters topics={[...topics.values()]} />
      <Masthead
        name={config.name}
        stories={byPlace.new.length}
        topics={paper.topics}
        counts={counts}
        section={shown}
        onSection={(id) => {
          flip.current = snapshot(grid.current)
          setSection(id)
        }}
        stack={
          paper.mode !== "loading" && (
            <StackButton ref={stack} count={Math.max(0, byPlace.later.length - flying)} onClick={() => setLaterOpen(true)} />
          )
        }
      />
      {paper.notice && <p className="notice">{paper.notice}</p>}

      {paper.mode !== "loading" && ready && (
        <main ref={grid} className="front" data-cols={across} data-phone={phone ? "" : undefined} style={{ "--cols": across } as CSSProperties}>
          {front.length === 0 && (
            <p className="empty">
              {sectionName ? `Nothing new in ${sectionName}. Ask your agent for more.` : "No stories yet. Ask your agent to find you some."}
            </p>
          )}
          {front.map((a) => {
            const place = layout.places.get(a.id)
            const rank = layout.rank.get(a.id) ?? 0
            return (
              <StoryCard
                key={a.id}
                article={a}
                topic={topicOf(a)}
                place={place}
                order={rank}
                shape={place ? drawnShape(place) : "small"}
                index={Math.min(rank, 12)}
                history={paper.history.get(a.id) ?? []}
                liked={a.like ? byId.get(a.like) : undefined}
                size={sizes.get(a.image) ?? undefined}
                live={live}
                enter={entering}
                opening={paper.opening.has(a.id)}
                tour={tour?.id === a.id ? tour.action : null}
                onOpen={(x) => setOpenId(x.id)}
                onAct={(action, x, el) => act(action, x, el)}
                onHold={(x) => setHoldId(x.id)}
              />
            )
          })}
        </main>
      )}

      {paper.mode !== "loading" && ready && (
        <footer className="colophon" role="status">
          {paper.mode === "sample" ? "Sample paper" : paper.lastChecked ? `Checked ${when(paper.lastChecked)}` : "Not checked yet"}
        </footer>
      )}

      <LaterSheet
        open={laterOpen}
        onOpenChange={setLaterOpen}
        phone={phone}
        later={byPlace.later}
        skipped={byPlace.skipped}
        topics={topics}
        history={paper.history}
        onOpen={(a) => {
          setLaterOpen(false)
          setOpenId(a.id)
        }}
        onTakeBack={(e) => {
          flip.current = snapshot(grid.current)
          paper.takeBack(e)
        }}
      />
      <StoryPage
        article={openArticle}
        topic={openArticle ? topicOf(openArticle) : undefined}
        history={openArticle ? (paper.history.get(openArticle.id) ?? []) : []}
        live={live}
        phone={phone}
        onClose={() => setOpenId(null)}
        onAct={choose}
        onTakeBack={(e) => paper.takeBack(e)}
      />
      <HoldSheet
        article={holdArticle}
        live={live}
        onClose={() => setHoldId(null)}
        onAct={choose}
        onOpen={(a) => {
          setHoldId(null)
          setOpenId(a.id)
        }}
      />
    </div>
  )
}
