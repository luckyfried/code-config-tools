import type { CSSProperties } from "react"
import { ArrowUpRight } from "lucide-react"
import type { Action, Article, InboxEvent, Topic } from "@/types"
import { choiceSays, clock } from "@/lib/words"
import { Brief } from "@/components/brief"
import { ChoiceButtons } from "@/components/choice-buttons"
import { Panel } from "@/components/panel"
import { Picture } from "@/components/picture"

/** One story on its own: the picture, the summary, the link to the original, the brief, the agent's notes, and
 * the history of the person's choices on it. */
export function StoryPage({
  article: a,
  topic,
  history,
  live,
  phone,
  onClose,
  onAct,
  onTakeBack,
}: {
  article: Article | null
  topic: Topic | undefined
  history: InboxEvent[]
  live: boolean
  phone: boolean
  onClose: () => void
  onAct: (action: Action, a: Article) => void
  onTakeBack: (e: InboxEvent) => void
}) {
  return (
    <Panel
      open={!!a}
      onOpenChange={(open) => !open && onClose()}
      phone={phone}
      kind="page"
      title={a?.headline ?? "Story"}
      description={a ? `${a.source}, ${a.minutes} minute read` : ""}
    >
      {a && topic && (
        <article className="pb-2" style={{ "--topic": topic.color, "--duo": `url(#duo-${topic.id})` } as CSSProperties}>
          <div className="relative aspect-[16/9] overflow-hidden bg-[var(--topic)] sm:rounded-t-sm">
            <Picture article={a} className="absolute inset-0" />
          </div>
          <div className="flex flex-col gap-4 px-0 pt-5 sm:px-8 sm:pt-7">
            <p className="kicker">
              <span className="kicker-topic">{topic.name}</span>
              <span>{a.source}</span>
              <span>{a.minutes} min read</span>
              <span>{clock(a.published_at)}</span>
            </p>
            <h2 className="font-serif text-[30px] leading-[1.08] font-bold tracking-tight text-balance sm:text-[38px]">{a.headline}</h2>
            <p className="text-[18px] leading-relaxed text-pretty">{a.summary.join(" ")}</p>
            <a
              className="inline-flex w-fit items-center gap-1.5 border-b-2 border-rule pb-0.5 font-sans text-[15px] font-semibold"
              href={a.link}
              target="_blank"
              rel="noreferrer"
            >
              Read it at {a.source}
              <ArrowUpRight className="size-4" aria-hidden="true" />
            </a>

            {a.deep && (
              <section className="mt-2 flex flex-col gap-4 border-t border-[var(--column-rule)] pt-5">
                <h3 className="font-sans text-xs font-bold tracking-[0.08em] text-muted-foreground uppercase">
                  The brief · {clock(a.deep.at)}
                </h3>
                <Brief deep={a.deep} topic={topic} />
              </section>
            )}

            {a.agent_notes.length > 0 && (
              <section className="flex flex-col gap-2 border-t border-[var(--column-rule)] pt-5">
                <h3 className="font-sans text-xs font-bold tracking-[0.08em] text-muted-foreground uppercase">From your agent</h3>
                {a.agent_notes.map((n, i) => (
                  <p key={i} className="text-[16px] leading-snug italic">
                    {n}
                  </p>
                ))}
              </section>
            )}

            <section className="flex flex-col gap-3 border-t border-[var(--column-rule)] pt-5">
              <h3 className="font-sans text-xs font-bold tracking-[0.08em] text-muted-foreground uppercase">Your choices</h3>
              {history.length === 0 ? (
                <p className="font-sans text-sm text-muted-foreground">None yet.</p>
              ) : (
                <ul className="history">
                  {history.map((e) => (
                      <li key={e.id} className="state" data-state={e.status}>
                        <span className="state-dot" aria-hidden="true" />
                        <span className="flex-1">
                          {choiceSays(e)} <span className="text-muted-foreground">{clock(e.at)}</span>
                        </span>
                        {e.status === "pending" && (
                          <button type="button" className="font-semibold text-foreground underline underline-offset-2" onClick={() => onTakeBack(e)}>
                            Take back
                          </button>
                        )}
                      </li>
                  ))}
                </ul>
              )}
              <ChoiceButtons live={live} onAct={(action) => onAct(action, a)} />
            </section>
          </div>
        </article>
      )}
    </Panel>
  )
}
