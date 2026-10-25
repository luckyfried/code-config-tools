import { format } from "date-fns"
import { Flame } from "lucide-react"
import type { Food, Macros } from "@/lib/config"
import { fmt, parseDay, shiftDay, totals, withinTarget, type Entry } from "@/lib/nutrition"
import { cn } from "@/lib/utils"
import { Rings } from "./Rings"

type Props = {
  today: string
  viewing: string
  days: Record<string, Entry[]>
  foods: Map<string, Food>
  targets: Macros
  onPick: (day: string) => void
  /** Milliseconds before the first day rises in; each next day follows 60 ms later. */
  delay?: number
  layout?: "stack" | "wide"
  /** The heading over the days, shown beside them when the week is laid out wide. */
  title?: React.ReactNode
}

export function WeekPanel({ today, viewing, days, foods, targets, onPick, delay = 0, layout = "stack", title }: Props) {
  const week = Array.from({ length: 7 }, (_, i) => shiftDay(today, i - 6)).map((key) => ({
    key,
    t: totals(days[key] ?? [], foods),
    logged: (days[key]?.length ?? 0) > 0,
  }))
  const logged = week.filter((d) => d.logged)
  const avg = (k: keyof Macros) => (logged.length ? logged.reduce((s, d) => s + d.t[k], 0) / logged.length : 0)

  let streak = 0
  const todayOn = withinTarget(totals(days[today] ?? [], foods).calories, targets.calories)
  for (let key = todayOn ? today : shiftDay(today, -1); ; key = shiftDay(key, -1)) {
    if (!withinTarget(totals(days[key] ?? [], foods).calories, targets.calories)) break
    streak++
    if (streak > 3660) break
  }

  const wide = layout === "wide"
  const low = Math.round(targets.calories * 0.9)
  const high = Math.round(targets.calories * 1.1)

  const strip = (
    <ol className={cn("grid grid-cols-7", wide ? "gap-2" : "gap-1")} aria-label="The last seven days">
      {week.map((d, i) => {
        const date = parseDay(d.key)
        const isToday = d.key === today
        return (
          <li key={d.key} className="day-in" ref={(el) => void el?.style.setProperty("--day-delay", `${delay + i * 60}ms`)}>
            <button
              type="button"
              onClick={() => onPick(d.key)}
              aria-current={d.key === viewing ? "date" : undefined}
              aria-label={`${format(date, "EEEE, MMMM d")}: ${fmt(d.t.calories)} kcal`}
              className={cn(
                "tile-press flex w-full flex-col items-center gap-2 rounded-xl px-1 py-2.5 outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
                d.key === viewing && "bg-muted",
              )}
            >
              <span className={cn("text-xs", isToday ? "font-semibold text-foreground" : "text-muted-foreground")}>
                {isToday ? "Today" : format(date, "EEE")}
              </span>
              <Rings
                size="mini"
                delay={delay + i * 60}
                className={cn("w-full", wide ? "max-w-[5.25rem]" : "max-w-14")}
                label=""
                values={{
                  calories: d.t.calories / targets.calories,
                  protein: d.t.protein / targets.protein,
                  carbs: d.t.carbs / targets.carbs,
                  fat: d.t.fat / targets.fat,
                }}
              />
              <span className={cn("text-xs tabular-nums", withinTarget(d.t.calories, targets.calories) ? "font-medium text-foreground" : "text-muted-foreground")}>
                {d.logged ? fmt(d.t.calories) : "–"}
              </span>
            </button>
          </li>
        )
      })}
    </ol>
  )

  const streakTitle = streak === 1 ? "1 day on target" : `${streak} days on target`
  const averagesTitle = `Daily average${logged.length ? `, ${logged.length} ${logged.length === 1 ? "day" : "days"} logged` : ""}`
  const averages = [
    <Avg key="c" label="Calories" value={avg("calories")} target={targets.calories} unit="kcal" bar="bg-energy" dense={wide} />,
    <Avg key="p" label="Protein" value={avg("protein")} target={targets.protein} unit="g" bar="bg-protein" dense={wide} />,
    <Avg key="cb" label="Carbs" value={avg("carbs")} target={targets.carbs} unit="g" bar="bg-carbs" dense={wide} />,
    <Avg key="f" label="Fat" value={avg("fat")} target={targets.fat} unit="g" bar="bg-fat" dense={wide} />,
  ]

  if (wide) {
    return (
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-4">
          {title}
          <section aria-labelledby="streak" className="ml-auto flex items-center gap-2.5">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-carbs/20 text-carbs-deep dark:text-carbs">
              <Flame className="size-4" aria-hidden="true" />
            </span>
            <h3 id="streak" className="text-sm font-semibold tabular-nums">
              {streakTitle}
            </h3>
            <p className="text-sm text-muted-foreground tabular-nums">
              {fmt(low)} to {fmt(high)} kcal
            </p>
          </section>
        </div>
        {strip}
        <section aria-label={averagesTitle} className="flex items-center gap-5 border-t pt-3">
          <h3 className="shrink-0 text-sm font-semibold">Daily average</h3>
          <dl className="grid flex-1 grid-cols-4 gap-5">{averages}</dl>
        </section>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {strip}
      <section aria-labelledby="streak" className="flex items-center gap-4 rounded-xl bg-muted p-4">
        <span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-carbs/20 text-carbs-deep dark:text-carbs">
          <Flame className="size-6" aria-hidden="true" />
        </span>
        <div className="flex flex-col">
          <h3 id="streak" className="text-lg font-semibold tabular-nums">
            {streakTitle}
          </h3>
          <p className="text-sm text-pretty text-muted-foreground">
            On target is {fmt(low)} to {fmt(high)} kcal.
          </p>
        </div>
      </section>

      <section aria-labelledby="averages" className="flex flex-col gap-3">
        <h3 id="averages" className="text-sm font-semibold">
          {averagesTitle}
        </h3>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-3">{averages}</dl>
      </section>
    </div>
  )
}

type AvgProps = { label: string; value: number; target: number; unit: string; bar: string; dense?: boolean }

function Avg({ label, value, target, unit, bar, dense }: AvgProps) {
  const pct = Math.min(1, target ? value / target : 0)
  return (
    <div className={cn("flex", dense ? "flex-row flex-wrap items-baseline gap-x-2 gap-y-1" : "flex-col gap-1")}>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className={cn("flex flex-col gap-1.5", dense && "contents")}>
        <span className={cn("font-semibold tabular-nums", dense ? "ml-auto text-base" : "text-lg")}>
          {fmt(value)} <span className="text-sm font-normal text-muted-foreground">{unit}</span>
        </span>
        <span className={cn("h-1.5 overflow-hidden rounded-full bg-muted-foreground/15", dense && "basis-full")} aria-hidden="true">
          <span className={cn("block h-full origin-left rounded-full", bar)} ref={(el) => void el?.style.setProperty("transform", `scaleX(${pct})`)} />
        </span>
      </dd>
    </div>
  )
}
