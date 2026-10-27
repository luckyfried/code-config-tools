import { ArrowUpRight, Check, Clock3, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { StateChip } from "@/components/state-chip"
import { ACTION_WORD, applyStage, foundOn, VIEW_ONLY, when } from "@/lib/board"
import type { Action, Card } from "@/types"

interface Props {
  card: Card | null
  phone: boolean
  busy: boolean
  problem?: string
  viewOnly: boolean
  onClose: () => void
  onChoose: (card: Card, action: Action) => void
}

export function JobDetail({ card, phone, busy, problem, viewOnly, onClose, onChoose }: Props) {
  return (
    <Sheet open={card !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent
        side={phone ? "bottom" : "right"}
        className={phone ? "max-h-[88dvh] rounded-t-2xl" : "w-[min(30rem,92vw)] sm:max-w-none"}
      >
        {card && <Body card={card} busy={busy} problem={problem} viewOnly={viewOnly} onChoose={onChoose} />}
      </SheetContent>
    </Sheet>
  )
}

function Body({ card, busy, problem, viewOnly, onChoose }: Pick<Props, "busy" | "problem" | "viewOnly" | "onChoose"> & { card: Card }) {
  const { job, shown, history } = card
  const made = history.filter((e) => e.status !== "cancelled").toReversed()
  const choices: { action: Action; label: string; icon: typeof Check }[] = [
    { action: "yes", label: "Yes", icon: Check },
    { action: "later", label: "Later", icon: Clock3 },
    { action: "no", label: "No", icon: X },
  ]
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto pad-safe-bottom">
      <SheetHeader className="gap-1.5 px-6 pt-7">
        <p className="text-sm font-semibold text-muted-foreground">
          {job.company} · found {foundOn(job.found_at)}
        </p>
        <SheetTitle className="font-heading text-2xl leading-tight font-semibold text-balance">{job.role}</SheetTitle>
        <SheetDescription className="text-base">
          {[job.location, job.remote === null ? null : job.remote ? "Remote" : "On site", job.pay]
            .filter(Boolean)
            .join(" · ")}
        </SheetDescription>
      </SheetHeader>

      <div className="flex flex-wrap gap-2 px-6 py-4">
        {choices.map(({ action, label, icon: Icon }) => (
          <Button
            key={action}
            variant={shown === action ? "secondary" : "outline"}
            disabled={busy || shown === action}
            onClick={() => onChoose(card, action)}
            className="h-10 px-4"
          >
            <Icon aria-hidden="true" />
            {shown === action ? `${label} now` : label}
          </Button>
        ))}
        <Button disabled={busy} onClick={() => onChoose(card, "apply")} className="h-10 px-4">
          Apply
          <ArrowUpRight aria-hidden="true" />
        </Button>
        {problem && <p className="w-full text-sm text-destructive">{problem}</p>}
        {viewOnly && <p className="w-full text-sm text-muted-foreground">{VIEW_ONLY}</p>}
      </div>

      <div className="flex flex-col gap-6 px-6 pb-8">
        {job.facts.length > 0 && (
          <section>
            <h4 className="mb-2 text-sm font-semibold">What stands out</h4>
            <ul className="flex flex-col gap-1.5 text-[0.9375rem] leading-relaxed">
              {job.facts.map((f) => (
                <li key={f} className="flex gap-2">
                  <span className="mt-[0.6em] size-1.5 shrink-0 rounded-full bg-primary" aria-hidden="true" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {job.agent_notes.length > 0 && (
          <section>
            <h4 className="mb-2 text-sm font-semibold">From your agent</h4>
            <div className="note flex flex-col gap-2 p-3.5 text-[0.9375rem] leading-relaxed">
              {job.agent_notes.map((n) => (
                <p key={n}>{n}</p>
              ))}
            </div>
          </section>
        )}

        <a
          href={job.link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 self-start font-semibold text-primary underline-offset-4 hover:underline"
        >
          Open the posting
          <ArrowUpRight className="size-4" aria-hidden="true" />
        </a>

        <Separator />

        <section>
          <h4 className="mb-3 text-sm font-semibold">Your choices</h4>
          {made.length === 0 ? (
            <p className="text-sm text-muted-foreground">No choices on this opening yet.</p>
          ) : (
            <ol className="flex flex-col gap-3">
              {made.map((e) => (
                <li key={e.id} className="flex flex-col items-start gap-1">
                  <div className="flex items-center gap-2">
                    {e.action === "apply" ? (
                      <StateChip stage={applyStage(e, job)} />
                    ) : (
                      <span className="text-sm font-semibold">{ACTION_WORD[e.action]}</span>
                    )}
                    <span className="text-[0.8125rem] text-muted-foreground">{when(e.at)}</span>
                  </div>
                  {e.status === "failed" && <p className="text-sm text-destructive">{e.error}</p>}
                </li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  )
}
