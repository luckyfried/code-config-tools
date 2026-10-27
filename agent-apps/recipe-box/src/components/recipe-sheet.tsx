import { useState } from "react"
import { Bookmark, CalendarPlus, ExternalLink, X } from "lucide-react"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { COPY } from "@/lib/copy"
import { DAY_SHORT, quantity, scaled, stateWords, target, type Slot } from "@/lib/box"
import type { Item } from "@/hooks/use-box"
import type { Day, InboxEvent } from "@/types"
import { Plates, TimeRing } from "@/components/time-ring"

interface Props {
  item: Item | null
  wide: boolean
  live: boolean
  household: number
  slots: Slot[]
  events: InboxEvent[]
  onClose: () => void
  onChoose: (action: "keep" | "skip" | "week", day?: Day) => void
}

const ACTION_WORDS = { keep: "Keep", skip: "Skip", week: "This week", "plan-week": "Plan the week" }

export function RecipeSheet(p: Props) {
  const [failed, setFailed] = useState<string | null>(null)
  const item = p.item
  const r = item?.record.body
  const factor = r ? p.household / Math.max(1, r.servings) : 1
  const history = item ? p.events.filter((e) => e.target === target(item.record.id)).reverse() : []
  return (
    <Sheet open={!!item} onOpenChange={(o) => !o && p.onClose()}>
      <SheetContent
        side={p.wide ? "right" : "bottom"}
        className="gap-0 overflow-y-auto p-0 data-[side=bottom]:max-h-[90dvh] data-[side=bottom]:rounded-t-2xl data-[side=right]:w-[30rem] data-[side=right]:sm:max-w-[30rem]"
      >
        {item && r && (
          <>
            <div className="relative shrink-0" style={{ background: r.color }}>
              {failed !== r.image ? (
                <img src={r.image} alt="" className="block max-h-[42dvh] w-full object-cover" onError={() => setFailed(r.image)} />
              ) : (
                <div className="grid h-48 place-items-center p-6 text-center font-heading text-3xl text-white">{r.title}</div>
              )}
            </div>
            <SheetHeader className="px-5 pb-2 pt-4">
              <SheetTitle className="pr-8 font-heading text-2xl font-normal leading-tight">{r.title}</SheetTitle>
              <SheetDescription className="flex items-center gap-2 text-sm">
                <TimeRing minutes={r.minutes} size={22} />
                <span>{r.minutes} minutes</span>
                <span className="opacity-40">·</span>
                <Plates servings={r.servings} />
                <span>serves {r.servings}</span>
              </SheetDescription>
            </SheetHeader>
            <div className="space-y-5 px-5 pb-6">
              {r.why && <p className="font-heading text-[1.0625rem] leading-snug text-accent-foreground">“{r.why}”</p>}
              <div className="flex gap-2">
                <button type="button" disabled={!p.live} onClick={() => p.onChoose("keep")}
                  data-on={item.shown.status === "kept" || undefined}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border bg-card py-2.5 text-sm font-semibold disabled:opacity-50 data-[on]:border-[var(--kept)] data-[on]:text-[var(--kept)]">
                  <Bookmark className="size-4" /> {COPY.keep}
                </button>
                <button type="button" disabled={!p.live} onClick={() => p.onChoose("skip")}
                  className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border bg-card py-2.5 text-sm font-semibold disabled:opacity-50">
                  <X className="size-4" /> {COPY.skip}
                </button>
              </div>
              <div>
                <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  <CalendarPlus className="size-3.5" /> Cook it this week
                </div>
                <div className="grid grid-cols-7 gap-1">
                  {p.slots.map((s) => (
                    <button key={s.day} type="button" disabled={!p.live} onClick={() => p.onChoose("week", s.day)}
                      data-on={(item.shown.status === "week" && item.shown.day === s.day) || undefined}
                      className="rounded-lg border bg-card py-2 text-xs font-semibold disabled:opacity-50 data-[on]:border-primary data-[on]:bg-primary data-[on]:text-primary-foreground">
                      {DAY_SHORT[s.day]}
                    </button>
                  ))}
                </div>
              </div>
              <section>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
                  Ingredients for {p.household}
                </h3>
                <ul className="divide-y">
                  {r.ingredients.map((ing, n) => (
                    <li key={n} className="flex items-baseline justify-between gap-3 py-1.5 text-sm">
                      <span>{ing.name}</span>
                      <span className="shrink-0 tabular-nums text-muted-foreground">
                        {quantity(scaled(ing.amount, ing.unit, factor), ing.unit) || "to taste"}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
              <section>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Steps</h3>
                <ol className="space-y-2 text-sm leading-relaxed">
                  {r.steps.map((s, n) => (
                    <li key={n} className="flex gap-3">
                      <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full bg-accent text-[0.6875rem] font-semibold text-accent-foreground">{n + 1}</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ol>
              </section>
              {r.agent_notes.length > 0 && (
                <section>
                  <h3 className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">From your agent</h3>
                  <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                    {r.agent_notes.map((n) => <li key={n}>{n}</li>)}
                  </ul>
                </section>
              )}
              {history.length > 0 && (
                <section>
                  <h3 className="mb-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">Your choices</h3>
                  <ul className="space-y-1 text-sm">
                    {history.map((e) => (
                      <li key={e.id} className="flex justify-between gap-3">
                        <span>{ACTION_WORDS[e.action]}{e.payload.day ? `, ${DAY_SHORT[e.payload.day]}` : ""}</span>
                        <span className="text-right text-muted-foreground">{stateWords(e)}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {r.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {r.tags.map((t) => <span key={t} className="rounded-full bg-muted px-2.5 py-0.5 text-xs text-muted-foreground">{t}</span>)}
                </div>
              )}
              {r.source && (
                <a href={r.source} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1.5 text-sm font-semibold text-primary underline-offset-4 hover:underline">
                  {COPY.fullRecipe} <ExternalLink className="size-3.5" />
                </a>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
