import { XIcon } from "lucide-react"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { cn } from "@/lib/utils"
import { MUSCLE_LABEL, type Exercise } from "@/lib/config"
import { bestE1rm, fmtE1rm, setsOf } from "@/lib/lift"
import { useLog } from "@/lib/log-context"

type Props = { onPicked?: () => void; className?: string; listClassName?: string; autoFocus?: boolean }

/** Every lift, searchable; the ones done today first; a muscle picked on the map narrows the list. */
export function ExercisePicker({ onPicked, className, listClassName, autoFocus }: Props) {
  const log = useLog()
  const { focus, setFocus } = log
  const doneToday = new Set(log.todaySets.map((s) => s.exercise))
  const pool = focus ? log.exercises.filter((e) => e.muscles.includes(focus)) : log.exercises
  const today = pool.filter((e) => doneToday.has(e.id))
  const rest = pool.filter((e) => !doneToday.has(e.id))

  const item = (e: Exercise) => {
    const best = bestE1rm(setsOf(log.sets, e.id))
    return (
      <CommandItem
        key={e.id}
        value={`${e.label} ${e.muscles.map((m) => MUSCLE_LABEL[m]).join(" ")} ${e.id}`}
        data-checked={e.id === log.selected.id}
        onSelect={() => {
          log.select(e.id)
          onPicked?.()
        }}
        className="min-h-12 gap-3 rounded-lg px-3 py-2"
      >
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-base font-medium">{e.label}</span>
          <span className="truncate text-xs text-muted-foreground">{e.muscles.map((m) => MUSCLE_LABEL[m]).join(", ")}</span>
        </div>
        {best > 0 ? (
          <span className="figures shrink-0 text-sm text-muted-foreground">
            {fmtE1rm(best)}
            <span className="text-xs"> {log.units}</span>
          </span>
        ) : null}
      </CommandItem>
    )
  }

  return (
    <Command className={cn("bg-transparent p-0", className)} loop>
      <CommandInput placeholder="Find a lift" autoFocus={autoFocus} className="text-base" />
      {focus ? (
        <div className="flex items-center gap-2 px-2 pt-2">
          <button
            type="button"
            onClick={() => setFocus(null)}
            className="press inline-flex h-8 items-center gap-1.5 rounded-full bg-secondary pr-2 pl-3 text-sm font-medium hover:bg-accent"
            aria-label={`Showing lifts for ${MUSCLE_LABEL[focus]}. Show every lift`}
          >
            {MUSCLE_LABEL[focus]}
            <XIcon className="size-4 text-muted-foreground" />
          </button>
          <span className="text-sm text-muted-foreground">
            {pool.length} {pool.length === 1 ? "lift" : "lifts"}
          </span>
        </div>
      ) : null}
      <CommandList className={cn("max-h-none", listClassName)}>
        <CommandEmpty>No lift by that name.</CommandEmpty>
        {today.length ? <CommandGroup heading="Today">{today.map(item)}</CommandGroup> : null}
        <CommandGroup heading={focus ? `Works the ${MUSCLE_LABEL[focus].toLowerCase()}` : today.length ? "Everything else" : "Your lifts"}>
          {rest.map(item)}
        </CommandGroup>
      </CommandList>
    </Command>
  )
}
