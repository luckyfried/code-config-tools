import { ForecastChart, ForecastKey } from "@/components/ForecastChart"
import { HeatWeeks } from "@/components/HeatStrip"
import { Totals } from "@/components/Totals"
import { config, type DayLog } from "@/lib/config"
import type { ForecastDay, Totals as T } from "@/lib/session"

export function ForecastView({ days, coming, log, now, totals }: { days: ForecastDay[]; coming: number; log: Record<string, DayLog>; now: string; totals: T }) {
  const week = days.slice(0, 7).reduce((n, d) => n + d.seen + d.fresh, 0)
  const month = days.reduce((n, d) => n + d.seen + d.fresh, 0)
  const title = `face-font-${config.font} text-lg font-semibold`
  return (
    <div className="mx-auto grid w-full max-w-[1200px] gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
      <section className="paper flex flex-col" data-ruled="no">
        <div className="paper-head">
          <h2 className={title}>The next 30 days</h2>
          <ForecastKey />
        </div>
        <div className="pt-3">
          <p className="tnum text-sm text-face-soft">
            {coming} of your {totals.cards} cards come up {month} times in all, {week} of them this week, if you answer each one Good.
          </p>
        </div>
        <div className="pt-6">
          <ForecastChart days={days} height={244} grow />
        </div>
      </section>
      <section className="paper">
        <div className="paper-head">
          <h2 className={title}>Where you stand</h2>
          <span className="tnum text-sm text-face-soft">{totals.cards} cards</span>
        </div>
        <Totals t={totals} />
      </section>
      <section className="paper overflow-x-auto lg:col-span-2" data-ruled="no">
        <div className="paper-head">
          <h2 className={title}>Every day you studied</h2>
          <span className="hidden text-sm text-face-soft sm:inline">One box a day for the last half year, darker for more cards.</span>
        </div>
        <div className="hidden pt-3 md:block">
          <HeatWeeks log={log} now={now} weeks={26} cell={16} animate />
        </div>
        <div className="pt-3 md:hidden">
          <HeatWeeks log={log} now={now} weeks={17} cell={15} animate />
        </div>
      </section>
    </div>
  )
}
