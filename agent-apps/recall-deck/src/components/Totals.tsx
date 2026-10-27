import { config } from "@/lib/config"
import type { Totals as T } from "@/lib/session"

// A ledger on the card's ruling: one figure a line, standing on it, then the deck as one bar split into its three parts.
export function Totals({ t }: { t: T }) {
  const tiles = [
    { label: "Due today", value: String(t.dueToday) },
    { label: "Answered, 30 days", value: String(t.answers30) },
    { label: "Recall", value: t.recall === null ? "–" : `${t.recall}%` },
    { label: "Day streak", value: String(t.streak) },
  ]
  // One count: the three parts are the deck's cards, so the segments and their labels always add up to t.cards.
  const parts = [
    { n: t.mature, label: "known well", tone: "var(--grade-4)" },
    { n: t.learning, label: "learning", tone: "var(--face-ink)" },
    { n: t.unseen, label: "not seen yet", tone: "color-mix(in oklch, var(--face-soft) 35%, transparent)" },
  ]
  const all = Math.max(1, t.cards)
  return (
    <div className="flex flex-col">
      {tiles.map((x) => (
        <div key={x.label} className="paper-row">
          <span className="text-sm text-face-soft">{x.label}</span>
          <span className="ledger-leader" aria-hidden="true" />
          <span className={`face-font-${config.font} tnum text-[22px] leading-none font-semibold`}>{x.value}</span>
        </div>
      ))}
      <div className="paper-row pb-[7px]">
        <div className="flex h-1.5 w-full overflow-hidden rounded-full" role="img" aria-label={`${t.cards} cards`}>
          {parts.map((x) => (
            <span key={x.label} className="h-full transition-[width] duration-500" style={{ width: `${(x.n / all) * 100}%`, background: x.tone }} />
          ))}
        </div>
      </div>
      <div className="paper-row tnum gap-x-3 overflow-hidden text-xs whitespace-nowrap text-face-soft">
        {parts.map((x) => (
          <span key={x.label} className="flex items-center gap-1.5">
            <span className="size-2 rounded-full" style={{ background: x.tone }} />
            {x.n} {x.label}
          </span>
        ))}
      </div>
    </div>
  )
}
