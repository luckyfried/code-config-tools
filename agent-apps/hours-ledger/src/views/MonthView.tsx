import { useState } from "react"
import { addMonths } from "date-fns"
import { ClientTotals } from "@/components/ClientTotals"
import { HeatLegend, MonthStrip } from "@/components/MonthStrip"
import { CountUp } from "@/components/CountUp"
import { Panel } from "@/components/Panel"
import { useLedger } from "@/lib/store"
import { HOUR, format, monthDays, msOnDay, useNow } from "@/lib/time"
import { PeriodNav } from "./PeriodNav"

export function MonthView({ onSelectDay }: { onSelectDay: (d: Date) => void }) {
  const ledger = useLedger()
  const now = useNow(1000)
  const [offset, setOffset] = useState(0)
  const days = monthDays(addMonths(new Date(now), offset))
  const perDay = days.map((d) => ledger.entries.reduce((a, e) => a + msOnDay(e, d, now), 0))
  const ms = perDay.reduce((a, b) => a + b, 0)
  const worked = perDay.filter((x) => x > 0).length
  const best = perDay.reduce((bi, x, i) => (x > perDay[bi] ? i : bi), 0)
  return (
    <div className="flex flex-col gap-4 sm:gap-5 xl:gap-6">
      <PeriodNav label={format(days[0], "MMMM yyyy")} onPrev={() => setOffset(offset - 1)} onNext={() => setOffset(offset + 1)} onNow={() => setOffset(0)} nowLabel="This month" />
      <Panel title="Hours by day" figure={<CountUp value={ms / HOUR} suffix=" h" delay={760} />} action={<HeatLegend />}>
        <MonthStrip key={offset} days={days} entries={ledger.entries} now={now} height={96} showHours onSelectDay={onSelectDay} />
        <dl className="grid grid-cols-3 gap-4 border-t border-rule pt-4">
          <Stat label="Days worked" value={String(worked)} />
          <Stat label="Average day" value={`${worked ? (ms / worked / HOUR).toFixed(1) : "0.0"} h`} />
          <Stat label="Longest day" value={ms ? `${format(days[best], "MMM d")}, ${(perDay[best] / HOUR).toFixed(1)} h` : "None yet"} />
        </dl>
      </Panel>
      <Panel title="By client" order={2}>
        <ClientTotals days={days} entries={ledger.entries} now={now} />
      </Panel>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-mono text-base font-medium text-balance tnum sm:text-lg">{value}</dd>
    </div>
  )
}
