import { useState } from "react"
import { ArrowLeftRight, X } from "lucide-react"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { TRAY_MAX } from "@/hooks/use-tray"
import { best, cell, commuteMinutes, priceLabel, ROW_NAMES } from "@/lib/board"
import type { AppConfig, Card } from "@/types"
import { Compare } from "./compare"

interface TrayProps {
  cards: Card[]
  config: AppConfig
  onAdd: (id: string) => void
  onRemove: (id: string) => void
  onCompare: () => void
}

export function DesktopTray({ cards, config, onAdd, onRemove, onCompare }: TrayProps) {
  const [over, setOver] = useState(false)
  const empty = TRAY_MAX - cards.length
  return (
    <aside
      className="tray"
      data-over={over ? "" : undefined}
      aria-label="Compare tray"
      onDragOver={(e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = "copy"
        setOver(true)
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        const id = e.dataTransfer.getData("text/plain")
        if (id) onAdd(id)
      }}
    >
      <div className="tray-head">
        <h2>Compare</h2>
        <span className="tray-count">
          {cards.length} of {TRAY_MAX}
        </span>
      </div>
      <ol className="slots">
        {cards.map((c) => (
          <li key={c.id} className="slot" data-tray-id={c.id}>
            <div className="slot-photo" style={{ background: c.home.color }}>
              {c.home.image && <img src={c.home.image} alt="" draggable={false} />}
            </div>
            <div className="slot-text">
              <p className="slot-title">{c.home.title}</p>
              <p className="slot-price">{priceLabel(c.home, config.currency)}</p>
            </div>
            <button type="button" className="slot-remove" aria-label={`Take ${c.home.title} out of compare`} onClick={() => onRemove(c.id)}>
              <X className="size-4" strokeWidth={2.4} />
            </button>
          </li>
        ))}
        {Array.from({ length: empty }, (_, n) => (
          <li key={`empty-${n}`} className="slot empty" data-slot-empty={n === 0 ? "" : undefined}>
            <span>{n === 0 ? "Drag a card here" : "Room for one more"}</span>
          </li>
        ))}
      </ol>
      {cards.length >= 2 ? (
        <button type="button" className="compare-go" onClick={onCompare}>
          <ArrowLeftRight className="size-4" strokeWidth={2.4} />
          Compare {cards.length} homes
        </button>
      ) : (
        <p className="compare-wait">Add {2 - cards.length === 1 ? "one more home" : "two homes"} to compare.</p>
      )}
      {cards.length > 0 && <Glance cards={cards} config={config} />}
      <div className="keys">
        <p>On a card</p>
        <ul>
          <li>
            <kbd>Y</kbd> yes
          </li>
          <li>
            <kbd>N</kbd> no
          </li>
          <li>
            <kbd>M</kbd> maybe
          </li>
          <li>
            <kbd>C</kbd> compare
          </li>
        </ul>
      </div>
    </aside>
  )
}

const GLANCE_ROWS = ["price", "price_per_area", "commute"] as const

// The tray's homes in three short rows, the best number in each lit, so the column reads before Compare opens.
function Glance({ cards, config }: { cards: Card[]; config: AppConfig }) {
  const homes = cards.map((c) => ({ id: c.id, home: c.home }))
  const names = ROW_NAMES(config.units)
  const rows = GLANCE_ROWS.filter((r) => config.compare_rows.includes(r))
  return (
    <table className="glance" style={{ ["--n" as string]: cards.length }}>
      <thead>
        <tr>
          <th scope="col">
            <span className="sr-only">Fact</span>
          </th>
          {cards.map((c) => (
            <th scope="col" key={c.id}>
              <span className="glance-dot" style={{ background: c.home.color }}>
                {c.home.image && <img src={c.home.image} alt={c.home.title} draggable={false} />}
              </span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const win = best(row, homes)
          return (
            <tr key={row}>
              <th scope="row">{names[row]}</th>
              {cards.map((c) => {
                const mins = row === "commute" ? commuteMinutes(c.home.commute) : null
                const v = row === "commute" ? (mins == null ? null : `${mins} min`) : cell(row, c.home, config.currency, config.units)
                return (
                  <td key={c.id} data-best={win.has(c.id) ? "" : undefined}>
                    {v ?? "–"}
                  </td>
                )
              })}
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export function PhoneTray({ cards, onRemove, onCompare }: Omit<TrayProps, "config" | "onAdd">) {
  const empty = TRAY_MAX - cards.length
  return (
    <div className="phone-tray" aria-label="Compare tray">
      <ol className="mini-slots">
        {cards.map((c) => (
          <li key={c.id} className="mini" data-tray-id={c.id} style={{ background: c.home.color }}>
            {c.home.image && <img src={c.home.image} alt="" />}
            <button type="button" aria-label={`Take ${c.home.title} out of compare`} onClick={() => onRemove(c.id)}>
              <X className="size-3" strokeWidth={3} />
            </button>
          </li>
        ))}
        {Array.from({ length: empty }, (_, n) => (
          <li key={`e-${n}`} className="mini empty" data-slot-empty={n === 0 ? "" : undefined} />
        ))}
      </ol>
      {cards.length >= 2 ? (
        <button type="button" className="compare-go" onClick={onCompare}>
          <ArrowLeftRight className="size-4" strokeWidth={2.4} />
          Compare {cards.length}
        </button>
      ) : (
        <p className="compare-wait">
          Tap <b>Compare</b> on {cards.length ? "one more home" : "two homes"}
        </p>
      )}
    </div>
  )
}

export function ComparePanel({
  cards,
  config,
  onRemove,
  onOpen,
  onClose,
}: {
  cards: Card[]
  config: AppConfig
  onRemove: (id: string) => void
  onOpen: (id: string) => void
  onClose: () => void
}) {
  return (
    <section className="compare-panel" aria-label="Compare">
      <div className="panel-head">
        <h2>Side by side</h2>
        <p>The best number in each row is lit.</p>
        <button type="button" className="panel-close" onClick={onClose} aria-label="Close compare">
          <X className="size-5" strokeWidth={2.4} />
        </button>
      </div>
      <Compare cards={cards} config={config} phone={false} onRemove={onRemove} onOpen={onOpen} />
    </section>
  )
}

export function CompareSheet({
  open,
  cards,
  config,
  onRemove,
  onOpen,
  onClose,
}: {
  open: boolean
  cards: Card[]
  config: AppConfig
  onRemove: (id: string) => void
  onOpen: (id: string) => void
  onClose: () => void
}) {
  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="bottom" className="compare-sheet">
        <SheetHeader className="sheet-head">
          <SheetTitle className="font-heading text-xl">Side by side</SheetTitle>
          <SheetDescription>The best number in each row is lit. Slide sideways to see every home.</SheetDescription>
        </SheetHeader>
        <Compare cards={cards} config={config} phone onRemove={onRemove} onOpen={onOpen} />
      </SheetContent>
    </Sheet>
  )
}
