import { useLayoutEffect, useRef, type CSSProperties } from "react"
import { ChevronDownIcon, RepeatIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { MUSCLE_LABEL } from "@/lib/config"
import { bestE1rm, e1rm, fmtE1rm, fmtWeight, recordDates } from "@/lib/lift"
import { useLog } from "@/lib/log-context"
import { Barbell } from "./Barbell"
import { SetChip } from "./SetChip"
import { Stepper } from "./Stepper"

const parseWeight = (t: string) => {
  const v = Number(t.replace(",", "."))
  return Number.isFinite(v) && v >= 0 ? v : null
}
const parseReps = (t: string) => {
  const v = Math.round(Number(t))
  return Number.isFinite(v) && v >= 1 ? v : null
}

const EQUIPMENT_NOTE = {
  dumbbell: "Weight is one dumbbell.",
  machine: "Weight is the stack or the sled.",
  bodyweight: "Weight is what you add to your body.",
}

type Props = { onPickExercise?: () => void; size?: "md" | "lg"; className?: string }

/** The exercise in hand: today's sets, the steppers, the plates, and the buttons that log. */
export function SessionCard({ onPickExercise, size = "md", className }: Props) {
  const log = useLog()
  const { selected, units, moment } = log
  const today = log.todaySets.filter((s) => s.exercise === selected.id)
  const records = recordDates(log.selectedSets)
  const best = bestE1rm(log.selectedSets)
  const muscles = selected.muscles.map((m) => MUSCLE_LABEL[m]).join(", ")
  const last = log.lastOfSelected
  const newest = today.at(-1)
  const lg = size === "lg"
  const row = useRef<HTMLDivElement>(null)
  const tail = useRef<HTMLSpanElement>(null)
  // The newest set stays in view at the end of the row, and the row starts on a whole set: the tail makes room to scroll that far.
  useLayoutEffect(() => {
    const el = row.current
    const end = tail.current
    if (!el || !end) return
    const align = () => {
      end.style.width = "0px"
      end.hidden = true
      const max = el.scrollWidth - el.clientWidth
      const chips = [...el.children].filter((c): c is HTMLElement => c !== end && c instanceof HTMLElement)
      if (max > 0 && chips.length > 1) {
        const origin = chips[0].offsetLeft
        const first = chips.find((c) => c.offsetLeft - origin >= max) ?? chips[chips.length - 1]
        const target = first.offsetLeft - origin
        end.hidden = false
        end.style.width = `${Math.max(0, target - (el.scrollWidth - el.clientWidth))}px`
        el.scrollLeft = target
      } else el.scrollLeft = 0
      el.classList.toggle("is-scrolled", el.scrollLeft > 0)
    }
    align()
    let alive = true
    void document.fonts?.ready.then(() => alive && align())
    let width = el.clientWidth
    const ro = new ResizeObserver(() => {
      if (el.clientWidth === width) return
      width = el.clientWidth
      align()
    })
    ro.observe(el)
    return () => {
      alive = false
      ro.disconnect()
    }
  }, [today.length, selected.id])

  return (
    <section
      aria-label={`Log ${selected.label}`}
      className={cn(
        "surface relative isolate flex flex-col gap-4 overflow-hidden rounded-2xl p-4",
        "short:grid short:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] short:items-stretch",
        lg && "gap-5 p-6",
        className,
      )}
    >
      {moment ? (
        <span key={moment.key} className="pr-sweep" aria-hidden style={{ "--pr-delay": `${moment.delay}ms` } as CSSProperties} />
      ) : null}

      {/* On a phone on its side the card splits: the lift and its bar on the left, the steppers and Log set on the right. */}
      <div className="contents short:flex short:min-w-0 short:flex-col short:gap-3">
        <header className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            {onPickExercise ? (
              <button
                type="button"
                onClick={onPickExercise}
                className="press -mx-1 flex max-w-full items-center gap-1 rounded-lg px-1 text-left hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
                aria-label={`${selected.label}. Choose another lift`}
              >
                <h2 className={cn("min-w-0 truncate font-semibold tracking-tight", lg ? "text-title" : "text-2xl")}>{selected.label}</h2>
                <ChevronDownIcon className="size-5 shrink-0 text-muted-foreground" />
              </button>
            ) : (
              <h2 className={cn("truncate font-semibold tracking-tight", lg ? "text-title" : "text-2xl")}>{selected.label}</h2>
            )}
            <p className="truncate text-sm text-muted-foreground">{muscles || "No muscles named"}</p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-1">
            {moment ? (
              <span
                key={moment.key}
                className="pr-chip pr-chip-in inline-flex h-7 items-center rounded-full px-2.5 text-sm font-bold"
                style={{ "--pr-delay": `${moment.delay}ms` } as CSSProperties}
              >
                PR
              </span>
            ) : null}
            <p className="figures text-sm text-muted-foreground">
              {moment ? (
                <span className="font-medium text-foreground">e1RM {fmtE1rm(moment.e1rm)} {units}</span>
              ) : best > 0 ? (
                <>Best e1RM {fmtE1rm(best)}</>
              ) : (
                "First time"
              )}
            </p>
          </div>
        </header>

        {selected.equipment === "barbell" ? (
          <Barbell key={selected.id} total={log.weight} bar={log.bar} plates={log.plates} units={units} size={size} />
        ) : null}

        <div
          ref={row}
          onScroll={(e) => e.currentTarget.classList.toggle("is-scrolled", e.currentTarget.scrollLeft > 0)}
          className="scroll-row -mx-1 flex min-h-9 items-center gap-1.5 overflow-x-auto px-1" aria-label="Today's sets of this lift">
          {today.length ? (
            today.map((s) => (
              <SetChip
                key={s.date}
                set={s}
                units={units}
                label={selected.label}
                record={records.has(s.date)}
                fresh={s === newest && !log.sample}
                editable={!log.sample}
              />
            ))
          ) : (
            <p className="text-sm text-muted-foreground">
              {last ? `Last time ${fmtWeight(last.weight)} ${units} × ${last.reps}` : "No sets yet. Set the weight and reps, then log."}
            </p>
          )}
          <span ref={tail} className="shrink-0 self-stretch" aria-hidden hidden />
        </div>
      </div>

      <div className="contents short:flex short:min-w-0 short:flex-col short:gap-3">
        <div className={cn("grid gap-3", lg ? "grid-cols-1 xl:grid-cols-[1.35fr_1fr]" : "grid-cols-[1.3fr_1fr] short:grid-cols-1")}>
          <Stepper
            id="weight"
            label="Weight"
            unit={units}
            value={log.weight}
            format={fmtWeight}
            parse={parseWeight}
            onStep={log.stepWeight}
            onSet={log.setWeight}
            decimal
            size={size}
            keys={lg ? "↑ ↓" : undefined}
          />
          <Stepper id="reps" label="Reps" value={log.reps} format={String} parse={parseReps} onStep={log.stepReps} onSet={log.setReps} size={size} keys={lg ? "← →" : undefined} />
        </div>

        {selected.equipment === "barbell" ? null : (
          <p className="text-sm text-muted-foreground">
            {EQUIPMENT_NOTE[selected.equipment]} Steps of {fmtWeight(log.step)} {units}.
          </p>
        )}

        <div className="flex gap-2 short:mt-auto">
          <Button className={cn("press min-w-0 flex-1 rounded-xl text-base font-semibold", lg ? "h-16 text-lg" : "h-14")} onClick={log.logSet} aria-keyshortcuts={lg ? "Enter" : undefined}>
            Log set
            <span className="figures font-normal opacity-70 max-md:short:hidden">
              {fmtWeight(log.weight)} × {log.reps}
            </span>
            {lg ? (
              <kbd className="key-hint key-hint--on-primary" aria-hidden>
                Enter
              </kbd>
            ) : null}
          </Button>
          <Button
            variant="secondary"
            className={cn("press rounded-xl px-5 text-base font-semibold", lg ? "h-16" : "h-14")}
            onClick={log.repeatSet}
            disabled={!last}
            aria-label={last ? `Repeat the last set, ${fmtWeight(last.weight)} ${units} for ${last.reps}` : "Repeat the last set"}
          >
            <RepeatIcon data-icon="inline-start" />+ set
          </Button>
        </div>
      </div>
      <span className="sr-only" aria-live="polite">
        {newest ? `Logged ${fmtWeight(newest.weight)} ${units} for ${newest.reps}, e1RM ${fmtE1rm(e1rm(newest.weight, newest.reps))}` : ""}
      </span>
    </section>
  )
}
