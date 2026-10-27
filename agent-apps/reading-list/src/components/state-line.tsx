import type { Article, InboxEvent } from "@/types"
import { choiceSays } from "@/lib/words"

/**
 * Seconds into its growth the ink line starts at, while the agent writes a brief the person asked for; null when no
 * brief is on the way. On the sample page it grows from the moment the page opens.
 */
export function writingSince(a: Article, history: InboxEvent[], live: boolean): number | null {
  if (a.deep) return null
  const asked = [...history].reverse().find((e) => e.action === "deeper" && ["pending", "working", "completed"].includes(e.status))
  if (!asked) return null
  if (!live) return 0
  return -Math.min(10, Math.max(0, (Date.now() - Date.parse(asked.at)) / 1000))
}

/** The latest choice on a story and where the agent is with it, in plain words. */
export function StateLine({ history, hasBrief }: { history: InboxEvent[]; hasBrief: boolean }) {
  const e = history[history.length - 1]
  if (!e) return null
  if (e.action === "deeper" && e.status === "completed" && hasBrief) return null
  return (
    <p className="state" data-state={e.status}>
      <span className="state-dot" aria-hidden="true" />
      <span>{choiceSays(e)}</span>
    </p>
  )
}
