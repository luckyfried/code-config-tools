import type { Action, Article } from "@/types"
import { ChoiceButtons } from "@/components/choice-buttons"
import { Panel } from "@/components/panel"

/** What a long press on a phone opens: the four choices on one story, and the way into it. */
export function HoldSheet({
  article: a,
  live,
  onClose,
  onAct,
  onOpen,
}: {
  article: Article | null
  live: boolean
  onClose: () => void
  onAct: (action: Action, a: Article) => void
  onOpen: (a: Article) => void
}) {
  return (
    <Panel
      open={!!a}
      onOpenChange={(open) => !open && onClose()}
      phone
      kind="page"
      title={a ? `Choices for ${a.headline}` : "Choices"}
      description="More like this, go deeper, read later, or skip."
    >
      {a && (
        <div className="flex flex-col gap-4">
          <p className="font-serif text-[22px] leading-tight font-semibold text-balance">{a.headline}</p>
          <ChoiceButtons live={live} onAct={(action) => onAct(action, a)} />
          <button
            type="button"
            className="min-h-12 rounded-sm bg-foreground font-sans text-[15px] font-semibold text-background"
            onClick={() => onOpen(a)}
          >
            Open the story
          </button>
        </div>
      )}
    </Panel>
  )
}
