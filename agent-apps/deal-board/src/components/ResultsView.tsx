import { Legend, WonLostChart } from "@/components/WonLostChart"
import { CompanyMark } from "@/components/CompanyMark"
import { money, plural, shortMoney, when } from "@/lib/format"
import { LOST, WON, closedAt, results, stageBefore, type Deal, type Stage } from "@/lib/pipeline"
import { cn } from "@/lib/utils"

/** Won and lost: ninety days of closed deals, the win rate, and how long a win takes from first entry to signature. */
export function ResultsView({ deals, stages, now, onOpen }: { deals: Deal[]; stages: Stage[]; now: number; onOpen: (id: string) => void }) {
  const r = results(deals, now)
  const closed = deals.filter((deal) => (closedAt(deal) ?? 0) >= now - 90 * 86_400_000).sort((a, b) => b.enteredAt - a.enteredAt)
  const longest = Math.max(1, ...r.cycles.map((cycle) => cycle.days))
  const label = (id: string) => stages.find((stage) => stage.id === id)?.label ?? id
  return (
    <div className="flex w-full flex-col gap-5 px-4 pt-2 pb-8 sm:px-6">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-xl font-semibold">Won and lost</h2>
        <span className="text-sm text-muted-foreground">Last 90 days</span>
      </div>

      <dl className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat term="Won" value={shortMoney(r.wonValue)} detail={plural(r.won, "deal")} tone="won" />
        <Stat term="Lost" value={shortMoney(r.lostValue)} detail={plural(r.lost, "deal")} tone="lost" />
        <Stat term="Win rate" value={r.winRate === null ? "None yet" : `${Math.round(r.winRate * 100)}%`} detail={`of ${plural(r.won + r.lost, "closed deal")}`} />
        <Stat term="Average cycle" value={r.averageCycle === null ? "None yet" : plural(Math.round(r.averageCycle), "day")} detail="from first entry to won" />
      </dl>

      <div className="grid gap-5 lg:grid-cols-[1.35fr_1fr]">
        <section className="flex flex-col gap-4 rounded-2xl border bg-card p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="font-semibold">By week</h3>
            <Legend won={r.wonValue} lost={r.lostValue} />
          </div>
          <WonLostChart weeks={r.weeks} tall className="flex-1" />
        </section>

        <section className="flex flex-col gap-4 rounded-2xl border bg-card p-5">
          <div className="flex items-baseline justify-between gap-2">
            <h3 className="font-semibold">Days to win</h3>
            {r.averageCycle !== null ? <span className="text-[13px] text-muted-foreground">Average {Math.round(r.averageCycle)}</span> : null}
          </div>
          {r.cycles.length === 0 ? (
            <p className="text-sm text-muted-foreground">Each deal you mark won shows here with the days it took.</p>
          ) : (
            <ol className="relative flex flex-col gap-2">
              {r.averageCycle !== null ? (
                <span
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-y-0 left-[calc(7.5rem+var(--at)*(100%-7.5rem-3.5rem))] w-px border-l border-dashed border-foreground/35"
                  style={{ "--at": r.averageCycle / longest } as React.CSSProperties}
                />
              ) : null}
              {r.cycles.map(({ deal, days }) => (
                <li key={deal.id} className="grid grid-cols-[7.5rem_1fr_3.5rem] items-center gap-0 text-sm">
                  <button type="button" onClick={() => onOpen(deal.id)} className="truncate pr-3 text-left hover:underline">
                    {deal.company}
                  </button>
                  <span className="h-3.5">
                    <span className="block h-full origin-left rounded-r-[4px] bg-won/85" style={{ width: `${Math.max(2, (days / longest) * 100)}%` }} />
                  </span>
                  <span className="text-right tabular-nums text-muted-foreground">{days}d</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>

      <section className="rounded-2xl border bg-card">
        <h3 className="px-5 pt-5 pb-2 font-semibold">Closed in the last 90 days</h3>
        <ul className="px-2 pb-2">
          {closed.length === 0 ? <li className="px-3 pb-3 text-sm text-muted-foreground">Nothing closed yet.</li> : null}
          {closed.map((deal) => (
            <li key={deal.id}>
              <button type="button" onClick={() => onOpen(deal.id)} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left hover:bg-muted/60">
                <CompanyMark company={deal.company} className="size-8 text-sm" />
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-medium">{deal.company}</span>
                  <span className="truncate text-[13px] text-muted-foreground">
                    {deal.stage === WON ? "Won" : `Lost at ${label(stageBefore(deal, stages))}`} {when(deal.enteredAt, now)}
                  </span>
                </span>
                <span className={cn("ml-auto flex shrink-0 items-center gap-2 font-medium tabular-nums", deal.stage === LOST && "text-muted-foreground")}>
                  <span className={cn("size-2 rounded-full", deal.stage === WON ? "bg-won" : "bg-lost")} />
                  {money(deal.value)}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function Stat({ term, value, detail, tone }: { term: string; value: string; detail: string; tone?: "won" | "lost" }) {
  return (
    <div className="flex flex-col gap-1 rounded-2xl border bg-card p-4">
      <dt className="flex items-center gap-2 text-[13px] text-muted-foreground">
        {tone ? <span className={cn("size-2 rounded-full", tone === "won" ? "bg-won" : "bg-lost")} /> : null}
        {term}
      </dt>
      <dd className="text-2xl font-semibold tracking-[-0.02em] tabular-nums sm:text-3xl">{value}</dd>
      <dd className="text-[13px] text-muted-foreground">{detail}</dd>
    </div>
  )
}
