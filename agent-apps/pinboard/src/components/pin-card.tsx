import { memo, useEffect, useLayoutEffect, useRef, useState, type CSSProperties } from "react"
import { Sparkles } from "lucide-react"
import { cn } from "cn"
import { ChoiceBar } from "@/components/choice-bar"
import { eventLine, hostOf, inkOn } from "@/lib/data"
import { arrive, fold, nod, pop } from "@/lib/motion"
import type { Action, BoardBody, PinView } from "@/types"

interface PinCardProps {
  pin: PinView
  boards: BoardBody[]
  boardName: (id: string | null) => string
  foundFor: string | null
  showBoard: boolean
  live: boolean
  busy: boolean
  ratio: number | undefined
  arrival: number | null
  folding: boolean
  open: boolean
  error: string | null
  onOpenChoices: (id: string | null) => void
  onDetail: (id: string) => void
  onChoose: (pin: PinView, action: Action, board?: string, name?: string) => void
  onFolded: (id: string) => void
  register: (id: string, el: HTMLElement | null) => void
}

const LONG_PRESS_MS = 450

function PinCardBase(props: PinCardProps) {
  const { pin, boards, boardName, foundFor, showBoard, live, busy, ratio, arrival, folding, open, error } = props
  const ref = useRef<HTMLElement | null>(null)
  const dot = useRef<HTMLSpanElement | null>(null)
  const [loaded, setLoaded] = useState(false)
  const [failed, setFailed] = useState(false)
  const [natural, setNatural] = useState<number | undefined>(undefined)
  const status = useRef(pin.status)
  const press = useRef<{ timer: number; x: number; y: number; long: boolean } | null>(null)

  useLayoutEffect(() => {
    if (ref.current && arrival !== null) arrive(ref.current, arrival)
    // A card arrives once, when it first mounts.
  }, [])

  useEffect(() => {
    if (status.current !== "kept" && pin.status === "kept") {
      if (ref.current) nod(ref.current)
      if (dot.current) pop(dot.current)
    }
    status.current = pin.status
  }, [pin.status])

  useEffect(() => {
    if (!folding || !ref.current) return
    let gone = false
    fold(ref.current).then(() => {
      if (!gone) props.onFolded(pin.id)
    })
    return () => {
      gone = true
    }
  }, [folding])

  const shownRatio = failed ? 0.8 : (natural ?? ratio ?? 0.8)
  const paint = { "--paint": pin.body.color, "--ratio": String(shownRatio) } as CSSProperties
  const host = hostOf(pin.body.source)
  const board = pin.board ? boardName(pin.board) : "Unsorted"

  const endPress = () => {
    if (press.current) window.clearTimeout(press.current.timer)
  }

  return (
    <article
      ref={(el) => {
        ref.current = el
        props.register(pin.id, el)
      }}
      data-open={open}
      style={paint}
      className="pin group relative cursor-pointer overflow-hidden bg-card text-card-foreground"
      onPointerDown={(event) => {
        if (event.pointerType === "mouse") return
        const x = event.clientX
        const y = event.clientY
        const timer = window.setTimeout(() => {
          if (press.current) press.current.long = true
          props.onOpenChoices(pin.id)
          navigator.vibrate?.(8)
        }, LONG_PRESS_MS)
        press.current = { timer, x, y, long: false }
      }}
      onPointerMove={(event) => {
        const start = press.current
        if (start && Math.hypot(event.clientX - start.x, event.clientY - start.y) > 10) endPress()
      }}
      onPointerUp={endPress}
      onPointerCancel={endPress}
      onContextMenu={(event) => event.preventDefault()}
      onClick={() => {
        if (press.current?.long) {
          press.current = null
          return
        }
        press.current = null
        if (open) props.onOpenChoices(null)
        else props.onDetail(pin.id)
      }}
      onKeyDown={(event) => {
        if (event.key === "Enter" && event.target === event.currentTarget) props.onDetail(pin.id)
      }}
      tabIndex={0}
      aria-label={pin.body.title}
    >
      <div className="paint relative">
        {failed ? (
          <div className="pin-image flex items-end p-3">
            <span className="font-display text-2xl leading-tight text-balance" style={{ color: inkOn(pin.body.color) }}>{pin.body.title}</span>
          </div>
        ) : (
          <img
            src={pin.body.image}
            alt=""
            draggable={false}
            width={400}
            height={Math.round(400 / shownRatio)}
            decoding="async"
            data-loaded={loaded}
            className="pin-image block h-auto w-full object-cover"
            onLoad={(event) => {
              const img = event.currentTarget
              if (img.naturalWidth && img.naturalHeight) setNatural(img.naturalWidth / img.naturalHeight)
              setLoaded(true)
            }}
            onError={() => setFailed(true)}
          />
        )}
        {pin.status === "kept" && (
          <span ref={dot} className="absolute top-2.5 right-2.5 size-3.5 rounded-full bg-kept ring-2 ring-card" aria-label="Kept" />
        )}
        {pin.asking && (
          <span className="breathing absolute top-2.5 left-2.5 inline-flex items-center gap-1 rounded-full bg-asking px-2.5 py-1 text-xs font-medium text-white shadow-sm">
            <Sparkles className="size-3.5" />
            Finding more
          </span>
        )}
        <ChoiceBar pin={pin} boards={boards} live={live} busy={busy} open={open} onChoose={(action, b, name) => props.onChoose(pin, action, b, name)} />
      </div>
      <div className="flex flex-col gap-1 px-3 pt-2.5 pb-3">
        <h3 className="line-clamp-2 text-sm leading-snug font-medium text-balance">{pin.body.title}</h3>
        <p className="truncate text-xs text-muted-foreground">
          {[host, showBoard ? board : null].filter(Boolean).join(" · ")}
        </p>
        {foundFor && (
          <p className="truncate text-xs text-asking">
            <Sparkles className="mr-1 inline size-3 align-[-0.125rem]" />
            More like {foundFor}
          </p>
        )}
        {error && <p className="text-xs text-pretty text-destructive">{error}</p>}
        {pin.latest && (
          <p
            className={cn(
              "text-xs text-pretty",
              pin.latest.status === "failed" ? "text-destructive" : "text-muted-foreground",
            )}
          >
            {eventLine(pin.latest, boardName, pin.found)}
          </p>
        )}
      </div>
    </article>
  )
}

export const PinCard = memo(PinCardBase)
