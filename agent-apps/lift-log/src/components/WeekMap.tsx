import type { CSSProperties } from "react"
import { cn } from "@/lib/utils"
import { MUSCLE_LABEL, type Muscle } from "@/lib/config"
import { fmtInt, fmtSets, LEVEL_LABEL } from "@/lib/lift"
import { useLog } from "@/lib/log-context"
import { BodyMap } from "./BodyMap"

/** The five shades and the sets each stands for; the compact one names only the ends. */
export function RampLegend({ compact, className }: { compact?: boolean; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <ul className="flex gap-1" aria-label="Shade by sets this week">
        {LEVEL_LABEL.map((label, i) => (
          <li key={label} className="flex min-w-0 flex-1 flex-col gap-1.5" aria-label={`${label} sets`}>
            <span className="ramp-swatch h-2 rounded-full" style={{ "--swatch": `var(--map-${i})` } as CSSProperties} />
            {compact ? null : <span className="figures text-center text-xs leading-none whitespace-nowrap text-muted-foreground">{label}</span>}
          </li>
        ))}
      </ul>
      {compact ? (
        <p className="flex justify-between text-xs leading-none text-muted-foreground" aria-hidden>
          <span>No sets</span>
          <span>12+</span>
        </p>
      ) : null}
    </div>
  )
}

type Props = { layout: "row" | "stack"; interactive?: boolean; onOpen?: () => void; className?: string }

/** This week's body map with the totals beside it: a row on a phone's session, a stack in the desktop's first pane. */
export function WeekMap({ layout, interactive, onOpen, className }: Props) {
  const log = useLog()
  const { week, focus, setFocus } = log
  const pick = interactive ? (m: Muscle) => setFocus(focus === m ? null : m) : undefined
  const top = [...week.muscles].sort((a, b) => b.sets - a.sets).filter((m) => m.sets > 0)
  const totals = (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-2">
      <div>
        <dt className="text-xs text-muted-foreground">Sets</dt>
        <dd className="figures text-title font-semibold tracking-tight">{week.sets}</dd>
      </div>
      <div>
        <dt className="text-xs text-muted-foreground">Days</dt>
        <dd className="figures text-title font-semibold tracking-tight">{week.sessions}</dd>
      </div>
      <div className="col-span-2">
        <dt className="text-xs text-muted-foreground">Moved</dt>
        <dd className="figures text-lg font-semibold">
          {fmtInt(week.volume)} <span className="text-sm font-normal text-muted-foreground">{log.units}</span>
        </dd>
      </div>
    </dl>
  )

  if (layout === "row") {
    return (
      <section className={cn("surface relative grid grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)] items-center gap-3 rounded-2xl p-3", className)} aria-label="This week">
        <BodyMap week={week.muscles} flash={log.flash} className="w-full" />
        <div className="flex min-w-0 flex-col gap-3 py-1 pr-1">
          <h2 className="text-sm font-medium">This week</h2>
          {totals}
          <RampLegend compact />
        </div>
        {onOpen ? (
          <button type="button" onClick={onOpen} className="absolute inset-0 rounded-2xl focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none" aria-label="Open this week" />
        ) : null}
      </section>
    )
  }

  return (
    <section className={cn("surface flex flex-col gap-4 rounded-2xl p-4", className)} aria-label="This week">
      <header className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">This week</h2>
        <span className="text-sm text-muted-foreground">Today and the six days before</span>
      </header>
      <BodyMap week={week.muscles} focus={focus} onPick={pick} flash={log.flash} className="mx-auto w-full max-w-[400px]" />
      <RampLegend />
      <div className="flex items-end justify-between gap-4">
        {totals}
        {focus ? (
          <p className="figures text-right text-sm text-pretty text-muted-foreground">
            <span className="font-medium text-foreground">{MUSCLE_LABEL[focus]}</span>
            <br />
            {fmtSets(week.muscles.find((m) => m.muscle === focus)?.sets ?? 0)} sets
          </p>
        ) : top.length ? (
          <p className="text-right text-sm text-pretty text-muted-foreground">
            Most work: <span className="font-medium text-foreground">{top.slice(0, 2).map((m) => MUSCLE_LABEL[m.muscle]).join(" and ")}</span>
          </p>
        ) : null}
      </div>
    </section>
  )
}

/** Sets and volume for each of the fourteen muscles, heaviest first; a tap lights its region. */
export function MuscleTable() {
  const log = useLog()
  const { week, focus, setFocus } = log
  const rows = [...week.muscles].sort((a, b) => b.sets - a.sets || b.volume - a.volume)
  return (
    <section className="surface overflow-hidden rounded-2xl" aria-label="Sets and volume by muscle">
      <div className="grid grid-cols-[1fr_4rem_6.5rem] gap-2 border-b px-4 py-2 text-xs text-muted-foreground">
        <span>Muscle</span>
        <span className="text-right">Sets</span>
        <span className="text-right">Volume ({log.units})</span>
      </div>
      <ul>
        {rows.map((r) => (
          <li key={r.muscle} className="border-b last:border-b-0">
            <button
              type="button"
              onClick={() => setFocus(focus === r.muscle ? null : r.muscle)}
              aria-pressed={focus === r.muscle}
              className={cn(
                "grid min-h-11 w-full grid-cols-[1fr_4rem_6.5rem] items-center gap-2 px-4 text-left hover:bg-accent focus-visible:bg-accent focus-visible:outline-none",
                focus === r.muscle && "bg-accent",
              )}
            >
              <span className="flex items-center gap-2.5">
                <span className="ramp-swatch size-3 rounded-full" style={{ "--swatch": `var(--map-${r.level})` } as CSSProperties} />
                <span className={cn("font-medium", r.sets === 0 && "text-muted-foreground")}>{MUSCLE_LABEL[r.muscle]}</span>
              </span>
              <span className="figures text-right">{fmtSets(r.sets)}</span>
              <span className="figures text-right text-muted-foreground">{fmtInt(r.volume)}</span>
            </button>
          </li>
        ))}
      </ul>
      <p className="border-t px-4 py-2.5 text-xs text-pretty text-muted-foreground">
        A set counts in full for a lift's first muscle and as half for the others.
      </p>
    </section>
  )
}
