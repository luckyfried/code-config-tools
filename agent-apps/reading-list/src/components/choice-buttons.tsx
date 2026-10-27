import { cn } from "@/lib/utils"
import type { Action } from "@/types"
import { ACTIONS } from "@/components/story-card"

/** The four choices as full buttons, for the story page and the long-press drawer. */
export function ChoiceButtons({
  live,
  onAct,
  className,
}: {
  live: boolean
  onAct: (action: Action) => void
  className?: string
}) {
  return (
    <div className={cn("grid grid-cols-2 gap-2", className)}>
      {ACTIONS.map(({ action, label, key, Icon }) => (
        <button
          key={action}
          type="button"
          aria-disabled={!live}
          className="flex min-h-12 items-center gap-2.5 rounded-sm border border-border bg-card px-3.5 text-left font-sans text-[15px] font-semibold transition-colors hover:bg-foreground hover:text-background aria-disabled:cursor-not-allowed"
          onClick={() => live && onAct(action)}
        >
          <Icon className="size-[18px] shrink-0" aria-hidden="true" />
          <span className="flex-1">{label}</span>
          <kbd className="hidden font-sans text-xs opacity-55 sm:inline">{key}</kbd>
        </button>
      ))}
    </div>
  )
}
