import { CountUp } from "@/components/CountUp"
import { ClientLegend } from "@/components/ClientLegend"
import { EntryRow } from "@/components/EntryRow"
import { HeatLegend, MonthStrip } from "@/components/MonthStrip"
import { Panel } from "@/components/Panel"
import { TimerCard } from "@/components/TimerCard"
import { WeekBars } from "@/components/WeekBars"
import { useLedger } from "@/lib/store"
import { HOUR, entriesOnDay, format, hm, monthDays, msOnDay, useNow, weekDays } from "@/lib/time"

export function TodayView({ onAddTime, onSelectDay }: { onAddTime: () => void; onSelectDay: (d: Date) => void }) {
  const ledger = useLedger()
  const now = useNow(1000)
  const today = new Date(now)
  const finished = entriesOnDay(ledger.entries, today, now).filter((e) => e.end !== null)
  const todayMs = ledger.entries.reduce((s, e) => s + msOnDay(e, today, now), 0)
  const week = weekDays(today)
  const weekMs = week.reduce((s, d) => s + ledger.entries.reduce((a, e) => a + msOnDay(e, d, now), 0), 0)
  const month = monthDays(today)
  const monthMs = month.reduce((s, d) => s + ledger.entries.reduce((a, e) => a + msOnDay(e, d, now), 0), 0)

  return (
    <div className="grid gap-4 sm:gap-5 lg:min-h-[calc(100dvh-8rem-1px)] lg:grid-cols-[minmax(0,7fr)_minmax(0,6fr)] xl:gap-6">
      <div className="flex min-w-0 flex-col gap-4 sm:gap-5 xl:gap-6">
        <TimerCard onAddTime={onAddTime} />
        <Panel title="Today" figure={`${hm(todayMs)} logged`} order={2} className="lg:flex-1">
          {finished.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground text-pretty">
              Finished timers land here. Pick a client above to start one.
            </p>
          ) : (
            <ul>
              {finished.map((e) => (
                <EntryRow key={e.id} entry={e} now={now} />
              ))}
            </ul>
          )}
        </Panel>
      </div>
      <div className="flex min-w-0 flex-col gap-4 sm:gap-5 xl:gap-6">
        <Panel title="This week" figure={<CountUp value={weekMs / HOUR} suffix=" h" />} order={1} className="lg:flex-1">
          <WeekBars days={week} entries={ledger.entries} now={now} height={340} fill onSelectDay={onSelectDay} />
          <ClientLegend />
        </Panel>
        <Panel title={format(today, "MMMM")} figure={<CountUp value={monthMs / HOUR} suffix=" h" delay={760} />} action={<HeatLegend />} order={3}>
          <MonthStrip days={month} entries={ledger.entries} now={now} height={52} onSelectDay={onSelectDay} />
        </Panel>
      </div>
    </div>
  )
}
