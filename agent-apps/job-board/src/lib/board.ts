import type { Action, AppConfig, Card, InboxEvent, Opportunity, Status, StoredRecord } from "@/types"

export const KIND = "opportunities"
export const STATUS_ACTIONS: Action[] = ["yes", "no", "later"]
const OPEN = new Set(["pending", "working"])

export const target = (id: string) => `${KIND}/${id}`

export function toJob(record: StoredRecord): Opportunity {
  const b = record.body
  return {
    id: record.id,
    role: b.role ?? "",
    company: b.company ?? "",
    link: b.link ?? "",
    location: b.location ?? "",
    pay: b.pay ?? "",
    remote: b.remote ?? null,
    facts: Array.isArray(b.facts) ? b.facts : [],
    found_at: b.found_at ?? record.at,
    status: (["new", "yes", "no", "later"] as Status[]).includes(b.status) ? b.status : "new",
    agent_notes: Array.isArray(b.agent_notes) ? b.agent_notes : [],
    applied_at: typeof b.applied_at === "string" ? b.applied_at : null,
  }
}

// The column a card sits in: the person's newest open choice, else the record's own status.
export function buildCards(records: StoredRecord[], events: InboxEvent[]): Card[] {
  const byTarget = new Map<string, InboxEvent[]>()
  for (const e of events) {
    if (!e.target) continue
    const list = byTarget.get(e.target)
    if (list) list.push(e)
    else byTarget.set(e.target, [e])
  }
  return records.map((record) => {
    const job = toJob(record)
    const history = (byTarget.get(target(record.id)) ?? []).toSorted((a, b) => a.at.localeCompare(b.at))
    let shown: Status = job.status
    for (const e of history) {
      if (OPEN.has(e.status) && STATUS_ACTIONS.includes(e.action)) shown = e.action as Status
    }
    return { record, job, shown, latest: history.at(-1) ?? null, history }
  })
}

// "<target>:<action>:<revision>", so the same tap twice is one event. A choice made again after its
// earlier event was cancelled gets a counted key, so it becomes a new event instead of the cancelled one.
export function choiceKey(card: Card, action: Action, events: InboxEvent[]): string {
  const base = `${target(card.record.id)}:${action}:${card.record.revision}`
  const same = events.filter((e) => e.key === base || e.key.startsWith(`${base}:`))
  const live = same.find((e) => e.status !== "cancelled" && e.status !== "failed")
  if (live) return live.key
  return same.length === 0 ? base : `${base}:${same.length}`
}

// When a card last moved: its newest choice, or the record's own change. A sorted column shows the newest first.
export function movedAt(card: Card): string {
  const choice = card.latest?.at ?? ""
  return choice > card.record.at ? choice : card.record.at
}

export function lastChecked(events: InboxEvent[]): string | null {
  let best: string | null = null
  for (const e of events) {
    if (e.status !== "completed") continue
    const t = e.result?.done_at ?? e.at
    if (!best || t > best) best = t
  }
  return best
}

export function sampleRecords(config: AppConfig): StoredRecord[] {
  return (config.sample ?? []).map((job, i) => ({
    id: job.id || `sample-${i + 1}`,
    kind: KIND,
    revision: 1,
    at: job.found_at,
    body: { ...job },
  }))
}

export function sampleEvents(config: AppConfig): InboxEvent[] {
  return (config.sampleInbox ?? []).map((s, i) => ({
    id: `sample-event-${i + 1}`,
    action: s.action,
    target: target(s.target),
    target_revision: 1,
    key: `${target(s.target)}:${s.action}:1`,
    at: s.at,
    payload: {},
    status: s.status,
    result: s.result ?? null,
    error: null,
  }))
}

const time = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit" })
const day = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" })

export function when(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  const now = new Date()
  return d.toDateString() === now.toDateString() ? `today at ${time.format(d)}` : `${day.format(d)} at ${time.format(d)}`
}

export function foundOn(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? "" : day.format(d)
}

export const ACTION_WORD: Record<Action, string> = { yes: "Yes", no: "No", later: "Later", apply: "Apply" }

// What a card says in place of its choices when the page has no board to send them to.
export const VIEW_ONLY = "View only. Ask your agent to start the board, then choose here."

// Where an apply is, as far as the board can know: waiting for the agent, taken up by the agent, recorded by the
// agent as sent, or refused. A move to yes, later, or no needs no chip, since its column says it.
export type ApplyStage = "waiting" | "agent" | "applied" | "failed"
export const APPLY_WORD: Record<ApplyStage, string> = {
  waiting: "Applying…",
  agent: "With your agent",
  applied: "Applied",
  failed: "Not applied",
}
export function applyStage(e: InboxEvent, job: Opportunity): ApplyStage {
  if (e.status === "failed") return "failed"
  if (job.applied_at && Date.parse(job.applied_at) >= Date.parse(e.at)) return "applied"
  return e.status === "pending" ? "waiting" : "agent"
}

// A new choice replaces the earlier pending ones it contradicts: a yes, no, or later replaces a different pending
// yes, no, or later, and a no or later also takes back a pending apply. An apply replaces nothing.
export function supersedes(earlier: InboxEvent, action: Action): boolean {
  if (earlier.status !== "pending" || action === "apply") return false
  return earlier.action === "apply" ? action !== "yes" : earlier.action !== action
}
