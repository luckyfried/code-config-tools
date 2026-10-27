import { X } from "lucide-react"
import { best, cell, ROW_NAMES } from "@/lib/board"
import type { AppConfig, Card } from "@/types"

// Two or three homes side by side, one row per fact, with the best number in each row lit. Nothing is sent.
export function Compare({
  cards,
  config,
  phone,
  onRemove,
  onOpen,
}: {
  cards: Card[]
  config: AppConfig
  phone: boolean
  onRemove: (id: string) => void
  onOpen: (id: string) => void
}) {
  const homes = cards.map((c) => ({ id: c.id, home: c.home }))
  const names = ROW_NAMES(config.units)
  const rows = config.compare_rows
  return (
    <div className="compare-scroll">
      <table className="compare" style={{ ["--n" as string]: cards.length }} data-phone={phone ? "" : undefined}>
        <thead>
          <tr>
            <th scope="col" className="row-name corner">
              <span className="sr-only">Fact</span>
            </th>
            {cards.map((c, n) => (
              <th scope="col" key={c.id} className="home-col" style={{ ["--c" as string]: n }}>
                <div className="cmp-photo" style={{ background: c.home.color }}>
                  {c.home.image && <img src={c.home.image} alt="" draggable={false} />}
                  <button type="button" className="cmp-remove" aria-label={`Take ${c.home.title} out of compare`} onClick={() => onRemove(c.id)}>
                    <X className="size-4" strokeWidth={2.6} />
                  </button>
                </div>
                <button type="button" className="cmp-title" onClick={() => onOpen(c.id)}>
                  {c.home.title}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => {
            const win = best(row, homes)
            return (
              <tr key={row} style={{ ["--r" as string]: r }}>
                <th scope="row" className="row-name">
                  {names[row]}
                </th>
                {cards.map((c) => {
                  const v = cell(row, c.home, config.currency, config.units)
                  const lit = win.has(c.id)
                  return (
                    <td key={c.id} data-best={lit ? "" : undefined} data-text={row === "place" || row === "commute" ? "" : undefined}>
                      <span className="v">{v ?? <span className="none">–</span>}</span>
                      {lit && <span className="best-tag">Best</span>}
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
