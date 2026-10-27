import type { KeyboardEvent, ReactNode } from "react"
import { CheckIcon, LockIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import type { Entrant } from "@/lib/bracket"
import { teamStyle } from "@/components/bracket-svg"

type Props = {
  id: string
  label: string
  players: [Entrant | null, Entrant | null]
  chosen: string | undefined
  locked: boolean
  waiting: string
  onChoose: (name: string) => void
  extra?: ReactNode
  note?: ReactNode
}

/** One match as two buttons, one per entrant; the chosen one fills with the entrant's color. */
export function MatchOptions({ id, label, players, chosen, locked, waiting, onChoose, extra, note }: Props) {
  return (
    <div className="surface flex flex-col gap-1.5 rounded-xl p-2.5">
      <div className="flex items-center justify-between px-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">
        <span>{label}</span>
        <span className="flex items-center gap-1.5">
          {note}
          {locked && <LockIcon className="size-3.5" aria-label="Decided" />}
        </span>
      </div>
      {players.map((e, slot) =>
        e ? (
          <button
            key={slot}
            type="button"
            data-nav={id}
            data-on={chosen === e.name}
            disabled={locked}
            aria-pressed={chosen === e.name}
            onClick={() => onChoose(e.name)}
            className={cn(
              "option flex h-11 items-center gap-2.5 rounded-lg border border-border bg-card pr-3 pl-3 text-left text-[0.95rem] transition-[background-color,border-color,transform] duration-150 outline-none hover:border-(--team) focus-visible:ring-[3px] focus-visible:ring-ring/60 active:scale-[0.98] disabled:cursor-default disabled:active:scale-100",
              locked && chosen !== e.name && "opacity-55",
            )}
            style={teamStyle(e.color)}
          >
            <span className="team-bar size-3 shrink-0 rounded-full" />
            <span className="figure w-5 shrink-0 text-xs text-muted-foreground">{e.seed}</span>
            <span className="min-w-0 flex-1 truncate font-medium">{e.name}</span>
            {chosen === e.name && <CheckIcon className="size-4 shrink-0" />}
          </button>
        ) : (
          <div key={slot} className="flex h-11 items-center rounded-lg border border-dashed border-border px-3 text-sm text-muted-foreground">
            {waiting}
          </div>
        ),
      )}
      {extra}
    </div>
  )
}

/** Arrow keys move between the pick buttons in reading order; Enter presses the focused one. */
export function navigate(e: KeyboardEvent<HTMLElement>) {
  const keys: Record<string, number> = { ArrowDown: 1, ArrowRight: 2, ArrowUp: -1, ArrowLeft: -2 }
  const step = keys[e.key]
  if (!step) return
  const all = [...e.currentTarget.querySelectorAll<HTMLButtonElement>("button[data-nav]:not(:disabled)")]
  const at = all.indexOf(document.activeElement as HTMLButtonElement)
  if (at < 0) return
  e.preventDefault()
  // Left and right jump to the same slot of the neighboring match.
  const target = Math.abs(step) === 2 ? at + Math.sign(step) * 2 : at + step
  all[Math.max(0, Math.min(all.length - 1, target))]?.focus()
}
