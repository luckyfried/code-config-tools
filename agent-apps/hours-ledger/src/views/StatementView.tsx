import { useState } from "react"
import { endOfMonth, endOfWeek, startOfMonth, startOfWeek, subMonths, subWeeks } from "date-fns"
import { CalendarIcon, PrinterIcon } from "lucide-react"
import type { DateRange } from "react-day-picker"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Label } from "@/components/ui/label"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { clientById, config, money, weekStartsOn } from "@/lib/config"
import { effectiveRounding, useLedger, type Entry } from "@/lib/store"
import { MINUTE, format, hm, inRange, roundedMinutes } from "@/lib/time"

type Preset = "this-month" | "last-month" | "this-week" | "last-week" | "custom"

function presetRange(p: Preset, now: Date): { from: Date; to: Date } {
  const o = { weekStartsOn }
  switch (p) {
    case "last-month":
      return { from: startOfMonth(subMonths(now, 1)), to: endOfMonth(subMonths(now, 1)) }
    case "this-week":
      return { from: startOfWeek(now, o), to: endOfWeek(now, o) }
    case "last-week":
      return { from: startOfWeek(subWeeks(now, 1), o), to: endOfWeek(subWeeks(now, 1), o) }
    default:
      return { from: startOfMonth(now), to: endOfMonth(now) }
  }
}

function periodLabel(from: Date, to: Date): string {
  if (from.getFullYear() !== to.getFullYear()) return `${format(from, "MMMM d, yyyy")} – ${format(to, "MMMM d, yyyy")}`
  if (from.getMonth() !== to.getMonth()) return `${format(from, "MMMM d")} – ${format(to, "MMMM d, yyyy")}`
  return `${format(from, "MMMM d")} – ${format(to, "d, yyyy")}`
}

export function StatementView() {
  const ledger = useLedger()
  const now = new Date()
  const firstWithHours = config.clients.find((c) => ledger.entries.some((e) => e.clientId === c.id && inRange(e, startOfMonth(now), endOfMonth(now))))
  const [clientId, setClientId] = useState((firstWithHours ?? config.clients[0]).id)
  const [preset, setPreset] = useState<Preset>("this-month")
  const [custom, setCustom] = useState<DateRange | undefined>()
  const range = preset === "custom" && custom?.from ? { from: custom.from, to: custom.to ?? custom.from } : presetRange(preset, now)
  const rounding = effectiveRounding(ledger)
  const lines = ledger.entries.filter((e) => e.clientId === clientId && inRange(e, range.from, range.to)).sort((a, b) => a.start - b.start)

  return (
    <div className="print-flat grid gap-5 lg:grid-cols-[20rem_minmax(0,1fr)] xl:gap-8">
      <aside className="no-print flex flex-col gap-5 lg:sticky lg:top-24 lg:self-start">
        <div className="flex flex-col gap-2">
          <Label htmlFor="statement-client">Client</Label>
          <Select value={clientId} onValueChange={setClientId}>
            <SelectTrigger id="statement-client" className="h-11 w-full text-base data-[size=default]:h-11">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                {config.clients.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-2">
          <Label>Period</Label>
          <ToggleGroup type="single" variant="outline" value={preset} onValueChange={(v) => v && setPreset(v as Preset)} className="grid w-full grid-cols-2">
            <ToggleGroupItem value="this-month" className="h-10">This month</ToggleGroupItem>
            <ToggleGroupItem value="last-month" className="h-10">Last month</ToggleGroupItem>
            <ToggleGroupItem value="this-week" className="h-10">This week</ToggleGroupItem>
            <ToggleGroupItem value="last-week" className="h-10">Last week</ToggleGroupItem>
          </ToggleGroup>
          <Popover>
            <PopoverTrigger asChild>
              <Button variant={preset === "custom" ? "secondary" : "outline"} className="h-10 justify-start font-normal">
                <CalendarIcon data-icon="inline-start" />
                {preset === "custom" ? periodLabel(range.from, range.to) : "Pick dates"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="range"
                weekStartsOn={weekStartsOn}
                selected={custom}
                defaultMonth={range.from}
                onSelect={(r) => {
                  setCustom(r)
                  setPreset("custom")
                }}
              />
            </PopoverContent>
          </Popover>
        </div>
        <Button size="lg" className="h-12 text-base" onClick={() => window.print()} disabled={lines.length === 0}>
          <PrinterIcon data-icon="inline-start" />
          Print statement
        </Button>
      </aside>
      <Sheet clientId={clientId} from={range.from} to={range.to} lines={lines} rounding={rounding} />
    </div>
  )
}

function Sheet({ clientId, from, to, lines, rounding }: { clientId: string; from: Date; to: Date; lines: Entry[]; rounding: number }) {
  const client = clientById(clientId)
  const rows = lines.map((e) => {
    const ms = (e.end as number) - e.start
    return { e, ms, minutes: roundedMinutes(ms, rounding) }
  })
  const rawMs = rows.reduce((s, r) => s + r.ms, 0)
  const totalMinutes = rows.reduce((s, r) => s + r.minutes, 0)
  const hoursBilled = Math.round((totalMinutes / 60) * 100) / 100
  const amount = Math.round(hoursBilled * client.rate * 100) / 100
  const roundingNote = rounding
    ? `Each entry is rounded up to the next ${rounding} minutes. Time as tracked: ${hm(rawMs)} (${(rawMs / MINUTE / 60).toFixed(2)} hours).`
    : `Hours are billed as tracked, to the minute.`

  return (
    <article
      aria-label="Statement"
      data-client={client.name}
      data-hours={hoursBilled.toFixed(2)}
      data-rate={client.rate}
      data-amount={amount.toFixed(2)}
      className="paper mx-auto w-full max-w-[52rem] rounded-sm border px-6 py-8 shadow-surface sm:px-14 sm:py-14 lg:px-[4.5rem] lg:py-16 print:px-[0.9in] print:py-[0.8in]"
    >
      <header className="flex items-start justify-between gap-6 text-[13px] leading-5">
        <div className="flex flex-col">
          <span className="font-semibold">{config.name}</span>
          <span className="opacity-60">Statement of hours</span>
        </div>
        <div className="flex flex-col text-right">
          <span className="opacity-60">Issued</span>
          <span>{format(Date.now(), "MMMM d, yyyy")}</span>
        </div>
      </header>

      <div className="mt-12 flex flex-col gap-1.5 sm:mt-16">
        <span className="text-[11px] leading-4 opacity-60">Prepared for</span>
        <h2 className="text-[28px] leading-9 font-semibold tracking-[-0.01em] text-balance">{client.name}</h2>
        <p className="text-[18px] leading-7">{periodLabel(from, to)}</p>
      </div>

      <table className="mt-10 w-full border-collapse text-[13px] leading-5">
        <thead>
          <tr className="border-b border-current/25 text-left text-[11px] leading-4">
            <th className="py-2 pr-4 font-medium opacity-70">Date</th>
            <th className="py-2 pr-4 font-medium opacity-70">Work</th>
            <th className="hidden py-2 pr-4 text-right font-medium opacity-70 sm:table-cell print:table-cell">Tracked</th>
            <th className="py-2 text-right font-medium opacity-70">Hours</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={4} className="py-10 text-center opacity-60">
                No hours for {client.name} in this period.
              </td>
            </tr>
          ) : (
            rows.map(({ e, ms, minutes }) => (
              <tr key={e.id} className="border-b border-current/10 align-top break-inside-avoid">
                <td className="py-2 pr-4 whitespace-nowrap">{format(e.start, "MMM d")}</td>
                <td className="py-2 pr-4">{e.note || "Work"}</td>
                <td className="hidden py-2 pr-4 text-right whitespace-nowrap opacity-60 sm:table-cell print:table-cell">{hm(ms)}</td>
                <td className="py-2 text-right whitespace-nowrap">{(minutes / 60).toFixed(2)}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      <div className="mt-8 ml-auto flex max-w-sm flex-col text-[13px] leading-5 break-inside-avoid">
        <div className="flex justify-between py-1.5">
          <span className="opacity-70">Hours</span>
          <span>{hoursBilled.toFixed(2)}</span>
        </div>
        <div className="flex justify-between py-1.5">
          <span className="opacity-70">Rate</span>
          <span>{money.format(client.rate)} an hour</span>
        </div>
        <div className="mt-2 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-t border-current/60 pt-4">
          <span className="text-[18px] leading-7 whitespace-nowrap">
            {hoursBilled.toFixed(2)} × {money.format(client.rate)}
          </span>
          <span className="text-[28px] leading-9 font-semibold tracking-[-0.01em]" data-line-total>
            {money.format(amount)}
          </span>
        </div>
      </div>

      <footer className="mt-14 flex flex-col gap-1 border-t border-current/15 pt-4 text-[11px] leading-4 opacity-70 break-inside-avoid">
        <p>{roundingNote}</p>
        {config.statementNote ? <p>{config.statementNote}</p> : null}
      </footer>
    </article>
  )
}
