import { useState } from "react"
import { addWeeks } from "date-fns"
import { ClientLegend } from "@/components/ClientLegend"
import { ClientTotals } from "@/components/ClientTotals"
import { CountUp } from "@/components/CountUp"
import { Panel } from "@/components/Panel"
import { WeekBars } from "@/components/WeekBars"
import { useLedger } from "@/lib/store"
import { HOUR, format, msOnDay, useNow, weekDays } from "@/lib/time"
import { PeriodNav } from "./PeriodNav"

export function WeekView({ onSelectDay }: { onSelectDay: (d: Date) => void }) {
  const ledger = useLedger()
  const now = useNow(1000)
  const [offset, setOffset] = useState(0)
  const days = weekDays(addWeeks(new Date(now), offset))
  const ms = days.reduce((s, d) => s + ledger.entries.reduce((a, e) => a + msOnDay(e, d, now), 0), 0)
  const label = `${format(days[0], "MMM d")} – ${format(days[6], days[0].getMonth() === days[6].getMonth() ? "d" : "MMM d")}`
  return (
    <div className="flex flex-col gap-4 sm:gap-5 xl:gap-6">
      <PeriodNav label={label} onPrev={() => setOffset(offset - 1)} onNext={() => setOffset(offset + 1)} onNow={() => setOffset(0)} nowLabel="This week" />
      <div className="grid gap-4 sm:gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] xl:gap-6">
        <Panel title="Hours by day" figure={<CountUp value={ms / HOUR} suffix=" h" />}>
          <WeekBars key={offset} days={days} entries={ledger.entries} now={now} height={380} onSelectDay={onSelectDay} />
          <ClientLegend />
        </Panel>
        <Panel title="By client" order={2}>
          <ClientTotals days={days} entries={ledger.entries} now={now} />
        </Panel>
      </div>
    </div>
  )
}
