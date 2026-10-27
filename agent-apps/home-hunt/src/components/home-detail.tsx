import { useEffect, useRef, useState } from "react"
import { ArrowUpRight, Bath, BedDouble, Check, Clock3, Paperclip, Plus, Ruler, X } from "lucide-react"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Textarea } from "@/components/ui/textarea"
import { day, hostOf, money, number, perArea, priceLabel, stateWords, unitWord } from "@/lib/board"
import type { Action, AppConfig, Card } from "@/types"
import { DrawnCheck } from "./marks"

export function HomeDetail({
  card,
  config,
  phone,
  live,
  focus,
  inTray,
  onClose,
  onChoose,
  onNote,
  onAsk,
  onTray,
}: {
  card: Card | null
  config: AppConfig
  phone: boolean
  live: boolean
  focus: "ask" | undefined
  inTray: boolean
  onClose: () => void
  onChoose: (card: Card, action: Action) => void
  onNote: (card: Card, text: string) => Promise<boolean>
  onAsk: (card: Card, question: string) => Promise<boolean>
  onTray: (id: string) => void
}) {
  return (
    <Sheet open={card != null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side={phone ? "bottom" : "right"} className="detail-sheet">
        {card && (
          <Detail
            key={card.id}
            card={card}
            config={config}
            live={live}
            focus={focus}
            inTray={inTray}
            onChoose={onChoose}
            onNote={onNote}
            onAsk={onAsk}
            onTray={onTray}
          />
        )}
      </SheetContent>
    </Sheet>
  )
}

function Detail({
  card,
  config,
  live,
  focus,
  inTray,
  onChoose,
  onNote,
  onAsk,
  onTray,
}: {
  card: Card
  config: AppConfig
  live: boolean
  focus: "ask" | undefined
  inTray: boolean
  onChoose: (card: Card, action: Action) => void
  onNote: (card: Card, text: string) => Promise<boolean>
  onAsk: (card: Card, question: string) => Promise<boolean>
  onTray: (id: string) => void
}) {
  const { home } = card
  const [noteText, setNoteText] = useState("")
  const [question, setQuestion] = useState("")
  const askRef = useRef<HTMLTextAreaElement>(null)
  const ppa = perArea(home)
  useEffect(() => {
    if (focus === "ask") window.setTimeout(() => askRef.current?.focus(), 250)
  }, [focus])

  const noteEvents = card.events.filter((e) => e.action === "note" && e.status !== "completed" && e.status !== "cancelled")
  const askEvents = card.events.filter(
    (e) => e.action === "ask" && e.status !== "cancelled" && !home.questions.some((q) => q.asked_at === e.at),
  )
  const history = card.events.slice().reverse()

  return (
    <div className="detail">
      <SheetHeader className="detail-head">
        <SheetTitle className="detail-title">{home.title}</SheetTitle>
        <SheetDescription className="detail-place">{home.place}</SheetDescription>
      </SheetHeader>
      <div className="detail-scroll">
        <div className="photo-strip" style={{ ["--paint" as string]: home.color }}>
          {home.photos.length ? (
            home.photos.map((p) => <img key={p} src={p} alt="" />)
          ) : (
            <div className="photo-empty" />
          )}
        </div>
        <div className="detail-facts">
          <p className="detail-price">
            {priceLabel(home, config.currency)}
            {ppa != null && (
              <span>
                {money(ppa, config.currency)} / {unitWord(config.units)}
              </span>
            )}
          </p>
          <ul className="detail-stats">
            <li>
              <BedDouble aria-hidden="true" /> {number(home.rooms)} bedrooms
            </li>
            <li>
              <Bath aria-hidden="true" /> {number(home.baths)} baths
            </li>
            <li>
              <Ruler aria-hidden="true" /> {home.area == null ? "Area not listed" : `${number(home.area)} ${unitWord(config.units)}`}
            </li>
            {home.commute && (
              <li>
                <Clock3 aria-hidden="true" /> {home.commute}
              </li>
            )}
          </ul>
          {home.source && (
            <a className="source-link" href={home.source} target="_blank" rel="noreferrer noopener">
              See the listing on {hostOf(home.source)} <ArrowUpRight aria-hidden="true" />
            </a>
          )}
        </div>
        <div className="detail-actions">
          {(["yes", "maybe", "no"] as const).map((a) => (
            <button
              key={a}
              type="button"
              className={`act act-${a}`}
              aria-pressed={card.shown === a}
              aria-disabled={!live ? true : undefined}
              onClick={() => onChoose(card, a)}
            >
              {a === "yes" ? <Check aria-hidden="true" /> : a === "no" ? <X aria-hidden="true" /> : <Paperclip aria-hidden="true" />}
              <span>{a === "yes" ? "Yes" : a === "no" ? "No" : "Maybe"}</span>
            </button>
          ))}
          <button type="button" className="act act-tray" aria-pressed={inTray} onClick={() => onTray(card.id)}>
            {inTray ? <Check aria-hidden="true" /> : <Plus aria-hidden="true" />}
            <span>{inTray ? "In compare" : "Compare"}</span>
          </button>
        </div>

        {home.checked.length > 0 && (
          <section className="detail-section">
            <h3>What your agent checked</h3>
            <ul className="checked-list">
              {home.checked.map((c, n) => (
                <li key={c.fact + n}>
                  <DrawnCheck delay={200 + n * 120} />
                  <span>{c.fact}</span>
                  <a href={c.source} target="_blank" rel="noreferrer noopener">
                    {hostOf(c.source)}
                  </a>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="detail-section">
          <h3>Your questions</h3>
          {home.questions.length === 0 && askEvents.length === 0 && (
            <p className="quiet">Ask the seller or the listing agent anything. Your agent shows you what it would send, and to whom, and sends it when you say so.</p>
          )}
          <ul className="qa-list">
            {home.questions.map((q) => (
              <li key={q.asked_at + q.question} data-waiting={q.answer == null ? "" : undefined}>
                <p className="q">{q.question}</p>
                {q.answer ? (
                  <p className="a">
                    {q.answer}
                    {q.answered_at && <span> {day(q.answered_at)}</span>}
                  </p>
                ) : (
                  <p className="wait">Waiting for the answer · asked {day(q.asked_at)}</p>
                )}
              </li>
            ))}
            {askEvents.map((e) => (
              <li key={e.id} data-waiting="">
                <p className="q">{String(e.payload.question ?? "")}</p>
                <p className="wait">{stateWords(e).label}</p>
              </li>
            ))}
          </ul>
          <form
            className="detail-form"
            onSubmit={async (ev) => {
              ev.preventDefault()
              if (!question.trim()) return
              if (await onAsk(card, question.trim())) setQuestion("")
            }}
          >
            <Textarea
              ref={askRef}
              value={question}
              maxLength={2000}
              rows={2}
              placeholder="Ask about this home, like when the roof was replaced"
              onChange={(e) => setQuestion(e.target.value)}
              aria-label="Your question"
            />
            <button type="submit" className="form-go" aria-disabled={!live || !question.trim() ? true : undefined}>
              Ask about this
            </button>
          </form>
        </section>

        <section className="detail-section">
          <h3>Your notes</h3>
          <ul className="note-list">
            {home.notes.map((n) => (
              <li key={n.at + n.text}>
                <p>{n.text}</p>
                <span>{day(n.at)}</span>
              </li>
            ))}
            {noteEvents.map((e) => (
              <li key={e.id} data-waiting="">
                <p>{String(e.payload.text ?? "")}</p>
                <span>{stateWords(e).label}</span>
              </li>
            ))}
          </ul>
          <form
            className="detail-form"
            onSubmit={async (ev) => {
              ev.preventDefault()
              if (!noteText.trim()) return
              if (await onNote(card, noteText.trim())) setNoteText("")
            }}
          >
            <Textarea
              value={noteText}
              maxLength={2000}
              rows={2}
              placeholder="A note for yourself and your agent"
              onChange={(e) => setNoteText(e.target.value)}
              aria-label="Your note"
            />
            <button type="submit" className="form-go" aria-disabled={!live || !noteText.trim() ? true : undefined}>
              Keep note
            </button>
          </form>
        </section>

        {home.agent_notes.length > 0 && (
          <section className="detail-section">
            <h3>Your agent's notes</h3>
            <ul className="agent-notes">
              {home.agent_notes.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
          </section>
        )}

        <section className="detail-section">
          <h3>Your choices</h3>
          {history.length === 0 ? (
            <p className="quiet">Found {day(home.found_at)}. No choices yet.</p>
          ) : (
            <ul className="history">
              {history.map((e) => {
                const w = stateWords(e)
                return (
                  <li key={e.id} className={`tone-${w.tone}`}>
                    <span className="dot" />
                    <span>
                      {w.label}
                      {w.detail && <em> {w.detail}</em>}
                    </span>
                    <time>{day(e.at)}</time>
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
