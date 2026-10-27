import { forwardRef, type CSSProperties } from "react"
import type { Article, InboxEvent, Topic } from "@/types"
import { Panel } from "@/components/panel"
import { Picture } from "@/components/picture"
import { StateLine } from "@/components/state-line"

/** The later stack in the corner: the saved stories, with a count that ticks up as each one lands. */
export const StackButton = forwardRef<HTMLButtonElement, { count: number; onClick: () => void }>(function StackButton(
  { count, onClick },
  ref,
) {
  return (
    <button ref={ref} type="button" className="stack" onClick={onClick} aria-label={`Read later: ${count} saved`}>
      <span className="stack-papers" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      <span className="stack-label">Later</span>
      <span className="stack-count">
        <span key={count}>{count}</span>
      </span>
    </button>
  )
})

function Row({
  a,
  topic,
  history,
  onOpen,
  onTakeBack,
}: {
  a: Article
  topic: Topic | undefined
  history: InboxEvent[]
  onOpen: (a: Article) => void
  onTakeBack: (e: InboxEvent) => void
}) {
  const pending = [...history].reverse().find((e) => (e.action === "later" || e.action === "skip") && e.status === "pending")
  return (
    <li className="list-row" style={{ "--topic": topic?.color, "--duo": topic ? `url(#duo-${topic.id})` : undefined } as CSSProperties}>
      <div className="list-pic">
        <Picture article={a} />
      </div>
      <div className="flex min-w-0 flex-col gap-1.5">
        <button type="button" className="list-headline text-left hover:underline" onClick={() => onOpen(a)}>
          {a.headline}
        </button>
        <p className="kicker">
          <span className="kicker-topic">{topic?.name}</span>
          <span>{a.source}</span>
          <span>{a.minutes} min</span>
        </p>
        <StateLine history={history} hasBrief={!!a.deep} />
        {pending && (
          <button
            type="button"
            className="w-fit font-sans text-sm font-semibold underline underline-offset-2"
            onClick={() => onTakeBack(pending)}
          >
            Put it back on the front page
          </button>
        )}
      </div>
    </li>
  )
}

export function LaterSheet({
  open,
  onOpenChange,
  phone,
  later,
  skipped,
  topics,
  history,
  onOpen,
  onTakeBack,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  phone: boolean
  later: Article[]
  skipped: Article[]
  topics: Map<string, Topic>
  history: Map<string, InboxEvent[]>
  onOpen: (a: Article) => void
  onTakeBack: (e: InboxEvent) => void
}) {
  const rows = (list: Article[]) => (
    <ul>
      {list.map((a) => (
        <Row key={a.id} a={a} topic={topics.get(a.topic)} history={history.get(a.id) ?? []} onOpen={onOpen} onTakeBack={onTakeBack} />
      ))}
    </ul>
  )
  return (
    <Panel open={open} onOpenChange={onOpenChange} phone={phone} kind="side" title="Read later" description="The stories you saved for later.">
      <h2 className="font-serif text-[34px] leading-none font-bold">Read later</h2>
      <p className="mt-2 mb-4 font-sans text-sm text-muted-foreground">
        {later.length === 0 ? "Nothing saved yet. Swipe a story right, or press L on it." : `${later.length} saved, newest first.`}
      </p>
      {rows(later)}
      {skipped.length > 0 && (
        <>
          <h3 className="mt-8 mb-2 font-sans text-xs font-bold tracking-[0.08em] text-muted-foreground uppercase">Skipped</h3>
          {rows(skipped)}
        </>
      )}
    </Panel>
  )
}
