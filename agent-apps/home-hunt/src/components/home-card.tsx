import { memo, useCallback, useState, type CSSProperties, type KeyboardEvent, type PointerEvent } from "react"
import { Bath, BedDouble, Check, Clock3, House, MessageCircleQuestion, Paperclip, Plus, Ruler, X } from "lucide-react"
import { useCountUp } from "@/hooks/use-count"
import { useSwipe } from "@/hooks/use-swipe"
import { money, number, perArea, stateWords, unitWord } from "@/lib/board"
import { tilt, untilt } from "@/lib/motion"
import type { Action, AppConfig, Card } from "@/types"
import { DrawnCheck, PaperClip, Seal } from "./marks"

// Cards that have made their entrance once; a card that moves between columns is not introduced again.
const arrived = new Set<string>()

export interface CardProps {
  card: Card
  config: AppConfig
  index: number
  phone: boolean
  live: boolean
  inTray: boolean
  problem: string | undefined
  busy: boolean
  onChoose: (card: Card, action: Action, from?: { x: number; y: number }) => void
  onTray: (id: string) => void
  onOpen: (id: string, focus?: "ask") => void
}

const BUTTONS: { action: "yes" | "maybe" | "no"; label: string; Icon: typeof Check; key: string }[] = [
  { action: "yes", label: "Yes", Icon: Check, key: "Y" },
  { action: "maybe", label: "Maybe", Icon: Paperclip, key: "M" },
  { action: "no", label: "No", Icon: X, key: "N" },
]

export const HomeCard = memo(function HomeCard(props: CardProps) {
  const { card, config, index, phone, live, inTray, problem, busy, onChoose, onTray, onOpen } = props
  const { home, shown } = card
  const [first] = useState(() => !arrived.has(card.id))
  const [photoOk, setPhotoOk] = useState(true)
  const delay = first ? index * 70 + 120 : 0
  const fmt = useCallback((n: number) => money(n, config.currency), [config.currency])
  const priceRef = useCountUp<HTMLSpanElement>(home.price, fmt, delay + 260, first)
  const swipeRef = useSwipe<HTMLElement>(phone, (action, from) => onChoose(card, action, from))
  const ppa = perArea(home)

  const question = home.questions.at(-1)
  const askEvent = card.events.filter((e) => e.action === "ask" && e.status !== "cancelled").at(-1)
  const pendingQuestion =
    askEvent && !home.questions.some((q) => q.asked_at === askEvent.at)
      ? (askEvent.payload.question as string | undefined)
      : undefined
  const shownQuestion = pendingQuestion ?? question?.question
  const answer = pendingQuestion ? null : (question?.answer ?? null)
  const lastChoice = card.events.filter((e) => e.action !== "ask").at(-1)
  // A finished or withdrawn choice says nothing on the card: the seal, the pile, or the column already shows it.
  const openState = (e: typeof lastChoice) => (e && (e.status === "pending" || e.status === "working" || e.status === "failed") ? stateWords(e) : null)
  const state = openState(lastChoice)
  const askState = openState(askEvent)

  const onKey = (e: KeyboardEvent<HTMLElement>) => {
    if (e.metaKey || e.ctrlKey || e.altKey || (e.target as Element).closest("textarea, input")) return
    const k = e.key.toLowerCase()
    if (k === "y" || k === "n" || k === "m") {
      e.preventDefault()
      onChoose(card, k === "y" ? "yes" : k === "n" ? "no" : "maybe")
    } else if (k === "c") {
      e.preventDefault()
      onTray(card.id)
    } else if (e.key === "Enter" && e.target === e.currentTarget) {
      e.preventDefault()
      onOpen(card.id)
    }
  }
  const onMove = (e: PointerEvent<HTMLElement>) => {
    if (e.pointerType !== "mouse" || phone) return
    const r = e.currentTarget.getBoundingClientRect()
    tilt(e.currentTarget, (e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height)
  }

  return (
    <article
      ref={swipeRef}
      data-card={card.id}
      data-shown={shown}
      className={`home-card${first ? " card-enter" : ""}`}
      style={{ "--i": index, "--paint": home.color } as CSSProperties}
      tabIndex={0}
      aria-label={`${home.title}, ${money(home.price, config.currency)}`}
      onKeyDown={onKey}
      onPointerMove={onMove}
      onPointerLeave={(e) => untilt(e.currentTarget)}
      onAnimationEnd={() => arrived.add(card.id)}
      draggable={!phone}
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", card.id)
        e.dataTransfer.effectAllowed = "copy"
        untilt(e.currentTarget)
      }}
    >
      <div className="card-lift" data-lift />
      {phone && (
        <div className="swipe-under" aria-hidden="true">
          <span className="u-yes">Yes</span>
          <span className="u-maybe">Maybe</span>
          <span className="u-no">No</span>
        </div>
      )}
      <div className="card-body">
        <div className="photo-wrap" data-photo>
          <button type="button" className="photo-clip" onClick={() => onOpen(card.id)} aria-label={`Open ${home.title}`}>
            {photoOk && home.image && (
              <img
                src={home.image}
                alt=""
                className="photo"
                draggable={false}
                decoding="async"
                loading={index < 4 ? "eager" : "lazy"}
                onError={() => setPhotoOk(false)}
              />
            )}
            {!(photoOk && home.image) && <House className="photo-none" strokeWidth={1.2} aria-hidden="true" />}
            <span className="photo-shade" />
            <span className="glint" />
          </button>
          {home.checked.length > 0 && (
            <ul className="fact-chips layer-near">
              {home.checked.slice(0, 1).map((c) => (
                <li key={c.fact} title={c.fact}>
                  <DrawnCheck delay={first ? delay + 650 : 0} />
                  <span>{c.fact}</span>
                </li>
              ))}
              {home.checked.length > 1 && (
                <li className="more">
                  <DrawnCheck delay={first ? delay + 870 : 0} />
                  <span>{home.checked.length - 1} more checked</span>
                </li>
              )}
            </ul>
          )}
          <button
            type="button"
            className="tray-toggle layer-mid"
            aria-pressed={inTray}
            aria-label={inTray ? `Take ${home.title} out of compare` : `Add ${home.title} to compare`}
            onClick={() => onTray(card.id)}
          >
            {inTray ? <Check className="size-4" strokeWidth={3} /> : <Plus className="size-4" strokeWidth={2.6} />}
            <span>{inTray ? "In compare" : "Compare"}</span>
          </button>
          <div className="price-tag layer-far">
            <span ref={priceRef} className="price">
              {money(home.price, config.currency)}
            </span>
            {home.period === "month" && <span className="per">/mo</span>}
            {ppa != null && (
              <span className="ppa">
                {money(ppa, config.currency)} / {unitWord(config.units)}
              </span>
            )}
          </div>
          <div className="seal" data-seal aria-hidden="true">
            <Seal />
          </div>
          {shown === "maybe" && (
            <div className="clip" aria-hidden="true">
              <PaperClip />
            </div>
          )}
        </div>
        <div className="info">
          <button type="button" className="title-btn" onClick={() => onOpen(card.id)}>
            <h3 className="title">{home.title}</h3>
          </button>
          <p className="place">{home.place}</p>
          <dl className="stats">
            <div>
              <dt className="sr-only">Bedrooms</dt>
              <BedDouble aria-hidden="true" />
              <dd>{number(home.rooms)} bd</dd>
            </div>
            <div>
              <dt className="sr-only">Baths</dt>
              <Bath aria-hidden="true" />
              <dd>{number(home.baths)} ba</dd>
            </div>
            <div>
              <dt className="sr-only">Floor area</dt>
              <Ruler aria-hidden="true" />
              <dd>{home.area == null ? "Area not listed" : `${number(home.area)} ${unitWord(config.units)}`}</dd>
            </div>
          </dl>
          {home.commute && (
            <p className="commute">
              <Clock3 aria-hidden="true" />
              {home.commute}
            </p>
          )}
          {shownQuestion && (
            <div className="ask-chip" data-waiting={answer == null ? "" : undefined}>
              <p className="q">
                <MessageCircleQuestion aria-hidden="true" />
                <span>{shownQuestion}</span>
              </p>
              <div className="answer-wrap" data-open={answer != null ? "" : undefined}>
                <div>
                  <p className="a">{answer ?? ""}</p>
                </div>
              </div>
              {answer == null && askState && <p className="ask-state">{askState.detail ?? askState.label}</p>}
            </div>
          )}
          {state && (
            <p className={`state-chip tone-${state.tone}`} key={`${lastChoice!.id}-${lastChoice!.status}`}>
              <span className="dot" />
              <span>
                {state.label}
                {state.detail && <span className="detail"> {state.detail}</span>}
              </span>
            </p>
          )}
          {problem && <p className="problem">{problem}</p>}
          <div className="actions" role="group" aria-label="Your choice">
            {BUTTONS.map(({ action, label, Icon, key }) => (
              <button
                key={action}
                type="button"
                className={`act act-${action}`}
                aria-pressed={shown === action}
                aria-disabled={!live || busy ? true : undefined}
                title={phone ? undefined : `${label} (${key})`}
                onClick={() => onChoose(card, action)}
              >
                <Icon aria-hidden="true" strokeWidth={2.4} />
                <span>{label}</span>
              </button>
            ))}
            <button type="button" className="act act-ask" onClick={() => onOpen(card.id, "ask")}>
              <MessageCircleQuestion aria-hidden="true" strokeWidth={2.2} />
              <span>Ask</span>
            </button>
          </div>
        </div>
      </div>
    </article>
  )
})
