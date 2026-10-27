import { useState } from "react"
import { PlayIcon, PlusIcon, SquareIcon } from "lucide-react"
import { cn } from "cn"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { clientById, clientColor, config } from "@/lib/config"
import { running, startTimer, stopTimer, updateEntry, useLedger } from "@/lib/store"
import { HOUR, clock, durationMs, format, hm, msOnDay, timeOfDay, useNow } from "@/lib/time"

const LONG = 12 * HOUR

export function TimerCard({ onAddTime }: { onAddTime: () => void }) {
  const ledger = useLedger()
  const now = useNow(1000)
  const current = running(ledger)
  const activeId = current?.clientId ?? ledger.lastClientId ?? config.clients[0].id
  const active = clientById(activeId)
  const elapsed = current ? durationMs(current, now) : 0
  const today = new Date(now)

  return (
    <section
      aria-label="Timer"
      data-running={current ? "true" : "false"}
      className="housing arrive relative rounded-[1.75rem] p-2 text-card-foreground sm:p-2.5 short:grid short:grid-cols-[minmax(0,1.12fr)_minmax(0,1fr)] short:gap-1"
      style={{ "--c": clientColor(activeId), "--i": 0 } as React.CSSProperties}
    >
      <div className="face rounded-[1.3rem] px-4 pt-5 pb-3.5 sm:px-7 sm:pt-7 sm:pb-6 2xl:px-10 2xl:pt-10 2xl:pb-9 short:flex short:flex-col short:justify-center short:px-6 short:pt-6 short:pb-5">
        <span className="band" aria-hidden />
        <div className="flex items-center gap-3">
          <span className="relative flex size-3 items-center justify-center" aria-hidden>
            {current ? <span className="halo absolute inset-0 rounded-full bg-(--c)" /> : null}
            <span
              className={cn(
                "relative size-3 rounded-full",
                current ? "breathe bg-(--c) shadow-[0_0_10px_var(--c)]" : "bg-current opacity-30",
              )}
            />
          </span>
          <span className="truncate text-base font-medium 2xl:text-lg">{current ? active.name : "No timer running"}</span>
          <span className="face-muted ml-auto shrink-0 text-sm tnum 2xl:text-base">
            {current ? `Since ${timeOfDay(current.start)}` : format(now, "EEEE, MMMM d")}
          </span>
        </div>

        <div
          role="timer"
          aria-live="off"
          className={cn(
            "light-up mt-3 mb-3.5 font-mono text-[length:min(64px,16.4vw)] leading-none font-medium tracking-tight tnum sm:mt-6 sm:mb-7 lg:text-[84px] 2xl:mt-10 2xl:mb-11 2xl:text-[124px] short:mt-5 short:mb-6 short:text-[68px]",
            current ? "lit" : "unlit",
          )}
        >
          {clock(elapsed)}
        </div>

        <Seconds lit={current ? Math.floor(elapsed / 1000) % 60 : -1} />
      </div>

      <div className="flex flex-col gap-4 px-2 pt-4 pb-2 sm:px-4 sm:pt-5 sm:pb-3.5 2xl:gap-5 2xl:px-5 2xl:pt-6 2xl:pb-5 short:justify-center short:gap-3 short:py-1 short:pr-1.5 short:pl-3">
        {current && elapsed > LONG ? <LongTimer start={current.start} /> : null}

        <Input
          aria-label="What you are working on"
          placeholder="What are you working on?"
          value={current?.note ?? ""}
          disabled={!current}
          onChange={(e) => current && updateEntry(current.id, { note: e.target.value })}
          className="h-11 bg-card/70 text-base shadow-[inset_0_1px_2px_oklch(0_0_0/0.08)] md:text-base 2xl:h-12"
        />

        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4 short:grid-cols-2 short:gap-2" role="group" aria-label="Clients">
          {config.clients.map((c) => {
            const on = current?.clientId === c.id
            const ms = ledger.entries.reduce((sum, e) => (e.clientId === c.id ? sum + msOnDay(e, today, now) : sum), 0)
            return (
              <button
                key={c.id}
                type="button"
                aria-pressed={on}
                onClick={() => (on ? undefined : startTimer(c.id))}
                style={{ "--c": clientColor(c.id) } as React.CSSProperties}
                className="key flex min-h-14 min-w-0 flex-col 2xl:min-h-16 short:min-h-13 items-start justify-center gap-0.5 rounded-xl px-2.5 py-2 text-left outline-none focus-visible:ring-3 focus-visible:ring-ring/50 sm:px-3"
              >
                <span className="flex w-full items-center gap-1.5 text-[13px] font-medium sm:gap-2 sm:text-sm">
                  <span className={cn("size-2.5 shrink-0 rounded-full bg-(--c)", on && "shadow-[0_0_8px_var(--c)]")} aria-hidden />
                  <span className="truncate" title={c.name}>{c.name}</span>
                </span>
                <span className="pl-4 font-mono text-xs text-muted-foreground tnum sm:pl-4.5">{hm(ms)} today</span>
              </button>
            )
          })}
        </div>

        <div className="flex items-center gap-2.5">
          {current ? (
            <Button size="lg" className="h-12 flex-1 rounded-xl text-base 2xl:h-14 shadow-[inset_0_1px_0_oklch(1_0_0/0.22),0_1px_0_oklch(0_0_0/0.25),0_6px_14px_-6px_oklch(0_0_0/0.5)]" onClick={() => stopTimer()}>
              <SquareIcon data-icon="inline-start" />
              Stop
              <kbd className="hidden rounded border border-current/30 px-1.5 font-mono text-xs opacity-60 lg:inline">S</kbd>
            </Button>
          ) : (
            <Button size="lg" className="h-12 flex-1 rounded-xl text-base 2xl:h-14 shadow-[inset_0_1px_0_oklch(1_0_0/0.22),0_1px_0_oklch(0_0_0/0.25),0_6px_14px_-6px_oklch(0_0_0/0.5)]" onClick={() => startTimer(activeId)}>
              <PlayIcon data-icon="inline-start" />
              Start {active.name}
              <kbd className="hidden rounded border border-current/30 px-1.5 font-mono text-xs opacity-60 lg:inline">S</kbd>
            </Button>
          )}
          <Button size="lg" variant="ghost" className="key h-12 rounded-xl px-4 text-base 2xl:h-14 2xl:px-5" onClick={onAddTime}>
            <PlusIcon data-icon="inline-start" />
            Add time
          </Button>
        </div>
      </div>
    </section>
  )
}

// The seconds scale under the readout: sixty ticks, lit up to the running second, every fifth one taller.
function Seconds({ lit }: { lit: number }) {
  return (
    <svg viewBox="0 0 600 12" preserveAspectRatio="none" className="block h-3 w-full" aria-hidden>
      {Array.from({ length: 60 }, (_, i) => (
        <rect key={i} x={i * 10 + 3.5} y={i % 5 === 0 ? 0 : 4} width={3} height={i % 5 === 0 ? 12 : 8} rx={1} className={i <= lit ? "tick-on" : "tick"} />
      ))}
    </svg>
  )
}

// A timer left on for more than twelve hours: end it at the time the work stopped.
function LongTimer({ start }: { start: number }) {
  const [time, setTime] = useState(() => format(start + 8 * HOUR, "HH:mm"))
  const end = () => {
    const [h, m] = time.split(":").map(Number)
    const d = new Date(start)
    d.setHours(h, m, 0, 0)
    let at = d.getTime()
    if (at <= start) at += 24 * HOUR
    stopTimer(at)
  }
  return (
    <div role="alert" className="flex flex-wrap items-center gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm">
      <span className="font-medium text-destructive">This timer has run over twelve hours.</span>
      <label className="flex items-center gap-2">
        End it at
        <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="h-9 w-32" />
      </label>
      <Button variant="destructive" onClick={end}>
        End here
      </Button>
    </div>
  )
}
