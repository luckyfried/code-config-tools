import { useRef, useState, type CSSProperties, type KeyboardEvent, type PointerEvent } from "react"
import { BookmarkPlus, EyeOff, PenLine, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Place, Shape } from "@/lib/pack"
import type { Action, Article, InboxEvent, Topic } from "@/types"
import { clock } from "@/lib/words"
import { Brief } from "@/components/brief"
import { Picture } from "@/components/picture"
import { StateLine, writingSince } from "@/components/state-line"

export const ACTIONS: { action: Action; label: string; key: string; Icon: typeof BookmarkPlus }[] = [
  { action: "later", label: "Later", key: "L", Icon: BookmarkPlus },
  { action: "skip", label: "Skip", key: "S", Icon: EyeOff },
  { action: "more", label: "More like this", key: "M", Icon: Sparkles },
  { action: "deeper", label: "Go deeper", key: "D", Icon: PenLine },
]

const KEYS: Record<string, Action> = { l: "later", s: "skip", m: "more", d: "deeper" }

interface Props {
  article: Article
  topic: Topic
  place: Place | undefined
  shape: Shape
  order: number
  index: number
  history: InboxEvent[]
  liked: Article | undefined
  size: { w: number; h: number } | undefined
  live: boolean
  enter: boolean
  opening: boolean
  tour: Action | null
  onOpen: (a: Article) => void
  onAct: (action: Action, a: Article, el: HTMLElement) => void
  onHold: (a: Article) => void
}

export function StoryCard(p: Props) {
  const { article: a, topic, place, shape } = p
  const ref = useRef<HTMLElement>(null)
  const gesture = useRef({ x: 0, y: 0, dx: 0, dragging: false, held: false, moved: false, timer: 0 })
  const [dragging, setDragging] = useState(false)
  const [side, setSide] = useState<"later" | "skip">("later")
  const writing = writingSince(a, p.history, p.live)

  const vars = {
    "--i": p.index,
    "--o": p.order,
    "--topic": topic.color,
    "--duo": `url(#duo-${topic.id})`,
    ...(place ? { "--c": place.c + 1, "--r": place.r + 1, "--cs": place.cs, "--rs": place.rs } : {}),
  } as CSSProperties

  const act = (action: Action) => ref.current && p.onAct(action, a, ref.current)

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.target !== e.currentTarget || e.metaKey || e.ctrlKey || e.altKey) return
    const action = KEYS[e.key.toLowerCase()]
    if (action) {
      e.preventDefault()
      act(action)
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault()
      p.onOpen(a)
    }
  }

  const g = gesture.current
  const reset = () => {
    window.clearTimeout(g.timer)
    g.dragging = false
    setDragging(false)
    ref.current?.style.setProperty("--dx", "0px")
  }
  const onPointerDown = (e: PointerEvent) => {
    if (e.pointerType === "mouse") return
    Object.assign(g, { x: e.clientX, y: e.clientY, dx: 0, dragging: false, held: false, moved: false })
    g.timer = window.setTimeout(() => {
      g.held = true
      p.onHold(a)
    }, 520)
  }
  const onPointerMove = (e: PointerEvent) => {
    if (e.pointerType === "mouse" || g.held) return
    const dx = e.clientX - g.x
    const dy = e.clientY - g.y
    if (Math.abs(dx) > 8 || Math.abs(dy) > 8) {
      g.moved = true
      window.clearTimeout(g.timer)
    }
    if (!g.dragging && Math.abs(dx) > 14 && Math.abs(dx) > Math.abs(dy) * 1.4) {
      g.dragging = true
      setDragging(true)
      ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    }
    if (g.dragging) {
      g.dx = dx
      setSide(dx >= 0 ? "later" : "skip")
      ref.current?.style.setProperty("--dx", `${dx}px`)
    }
  }
  const onPointerUp = () => {
    window.clearTimeout(g.timer)
    if (!g.dragging) return
    const width = ref.current?.getBoundingClientRect().width ?? 1
    const dx = g.dx
    reset()
    if (dx > width * 0.3) act("later")
    else if (dx < -width * 0.3) act("skip")
  }
  const onClick = () => {
    if (g.moved || g.held) {
      g.moved = false
      g.held = false
      return
    }
    p.onOpen(a)
  }

  const summary = shape === "long" ? null : (
    <p className="summary">
      {a.summary.map((s, i) => (
        <span key={i} className="sentence" style={{ "--s": i } as CSSProperties}>
          {s}{" "}
        </span>
      ))}
    </p>
  )

  return (
    <article
      ref={ref}
      data-story={a.id}
      data-shape={shape}
      data-edge={place && place.c === 0 ? "first" : undefined}
      data-tour={p.tour ?? undefined}
      className={cn("story", p.enter && "enter", p.opening && "is-opening", dragging && "is-dragging")}
      style={vars}
      tabIndex={0}
      aria-label={`${a.headline}, ${a.source}`}
      onKeyDown={onKeyDown}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={reset}
      onClick={onClick}
      onContextMenu={(e) => e.preventDefault()}
    >
      <div className="under" data-side={side} aria-hidden="true">
        {side === "later" ? "Read later" : "Skip"}
      </div>
      <div className="story-inner">
        <div className="pic">
          <Picture article={a} size={p.size} duotone />
          <div className="actions" onClick={(e) => e.stopPropagation()}>
            {ACTIONS.map(({ action, label, key, Icon }) => (
              <button
                key={action}
                type="button"
                className="act"
                data-pressed={p.tour === action ? "" : undefined}
                aria-label={`${label} (${key})`}
                title={`${label} (${key})`}
                tabIndex={-1}
                onClick={() => act(action)}
              >
                <Icon aria-hidden="true" />
                {shape === "small" ? action === "more" ? "More" : action === "deeper" ? "Deeper" : label : label}
              </button>
            ))}
          </div>
        </div>
        <div className="story-body">
          <p className="kicker">
            <span className="kicker-topic">{topic.name}</span>
            <span>{a.source}</span>
            <span>{a.minutes} min</span>
          </p>
          <h2 className="headline">
            <span className="hl-size" aria-hidden="true">
              {a.headline}
            </span>
            <span className="hl">{a.headline}</span>
          </h2>
          {writing !== null && <div className="ink" style={{ "--since": `${writing}s` } as CSSProperties} />}
          {shape === "long" && <p className="deck">{a.summary[0]}</p>}
          {summary}
          {shape === "long" && a.deep && <Brief deep={a.deep} topic={topic} />}
          {p.liked && shape !== "small" && (
            <p className="kicker">
              <span className="kicker-like">Found because you asked for more like “{p.liked.headline}”</span>
            </p>
          )}
          {writing !== null ? (
            <p className="writing">The agent is writing the brief.</p>
          ) : (
            <StateLine history={p.history} hasBrief={!!a.deep} />
          )}
          {shape === "long" && a.deep && <p className="brief-by">Brief by your agent · {clock(a.deep.at)}</p>}
        </div>
      </div>
    </article>
  )
}
