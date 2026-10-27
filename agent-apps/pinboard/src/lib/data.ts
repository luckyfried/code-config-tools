import type { Action, BoardBody, Filter, InboxEvent, PinBody, PinView, StoredRecord } from "@/types"

export const slug = (name: string) =>
  name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64) || "board"

export const ACTION_LABEL: Record<Action, string> = {
  keep: "Keep",
  reject: "Set aside",
  move: "Move",
  "find-more": "More like this",
}

const STATE_WORDS: Record<InboxEvent["status"], string> = {
  pending: "pending, the agent picks it up when you ask",
  working: "working, the agent has it now",
  completed: "completed",
  failed: "failed",
  cancelled: "cancelled",
}

/** The plain line a card shows for its latest choice. */
export function eventLine(event: InboxEvent, boardName: (id: string | null) => string, found = 0): string {
  const what = event.action === "move" ? `Move to ${event.payload.name || boardName(event.payload.board ?? null)}` : ACTION_LABEL[event.action]
  if (event.status === "completed") {
    if (event.action === "find-more") return `${found} more like this`
    const said = event.result?.said
    return said ? `${what}, completed: ${said}` : `${what}, completed`
  }
  if (event.status === "failed") return `${what}, failed: ${event.error ?? "the agent could not do it"}`
  return `${what}, ${STATE_WORDS[event.status]}`
}

export function hostOf(link: string): string {
  try {
    return new URL(link).hostname.replace(/^www\./, "")
  } catch {
    return ""
  }
}

export function timeWords(iso: string): string {
  const when = new Date(iso)
  const now = new Date()
  const time = when.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
  if (when.toDateString() === now.toDateString()) return `today at ${time}`
  return `${when.toLocaleDateString(undefined, { month: "short", day: "numeric" })} at ${time}`
}

/** Pins in wall order: the order they were added, with each find placed right after the pin it was found for. */
export function wallOrder<T extends { id: string; body: PinBody }>(pins: T[]): T[] {
  const ids = new Set(pins.map((pin) => pin.id))
  const finds = new Map<string, T[]>()
  const roots: T[] = []
  for (const pin of pins) {
    const parent = pin.body.found_for
    if (parent && parent !== pin.id && ids.has(parent)) {
      finds.set(parent, [...(finds.get(parent) ?? []), pin])
    } else {
      roots.push(pin)
    }
  }
  const out: T[] = []
  const place = (pin: T) => {
    out.push(pin)
    for (const find of finds.get(pin.id) ?? []) place(find)
  }
  roots.forEach(place)
  return out
}

/** Lays each pin's latest open choice over its stored state, so a tap shows at once. */
export function viewPins(records: StoredRecord<PinBody>[], events: InboxEvent[]): PinView[] {
  const byTarget = new Map<string, InboxEvent[]>()
  for (const event of events) {
    if (!event.target) continue
    byTarget.set(event.target, [...(byTarget.get(event.target) ?? []), event])
  }
  const sorted = [...records].sort((a, b) => (a.body.added ?? "").localeCompare(b.body.added ?? ""))
  return wallOrder(sorted).map((record) => {
    const history = (byTarget.get(`pins/${record.id}`) ?? []).slice().sort((a, b) => b.at.localeCompare(a.at))
    const latest = history[0] ?? null
    let status = record.body.status
    let board = record.body.board ?? null
    for (const event of history.filter((e) => e.status === "pending" || e.status === "working").reverse()) {
      if (event.action === "keep") status = "kept"
      if (event.action === "reject") status = "rejected"
      if (event.action === "move" && event.payload.board) board = event.payload.board
    }
    const ask = history.find((e) => e.action === "find-more" && e.status !== "cancelled" && e.status !== "failed")
    const answered = ask
      ? records.some((other) => other.body.found_for === record.id && (other.body.added ?? other.at) > ask.at)
      : true
    const found = records.filter((other) => other.body.found_for === record.id).length
    return { id: record.id, revision: record.revision, body: record.body, status, board, latest, history, asking: !answered, found }
  })
}

export function matches(pin: PinView, filter: Filter, boards: Set<string>): boolean {
  if (filter.kind === "set-aside") return pin.status === "rejected"
  if (pin.status === "rejected") return false
  if (filter.kind === "board") return pin.board === filter.id
  if (filter.kind === "unsorted") return !pin.board || !boards.has(pin.board)
  if (filter.kind === "tag") return pin.body.tags.includes(filter.tag)
  return true
}

export function readFilter(hash: string): Filter {
  const [, kind, value] = hash.replace(/^#/, "").split("/")
  if (kind === "board" && value) return { kind: "board", id: decodeURIComponent(value) }
  if (kind === "tag" && value) return { kind: "tag", tag: decodeURIComponent(value) }
  if (kind === "set-aside") return { kind: "set-aside" }
  if (kind === "unsorted") return { kind: "unsorted" }
  return { kind: "all" }
}

export function filterHash(filter: Filter): string {
  if (filter.kind === "board") return `#/board/${encodeURIComponent(filter.id)}`
  if (filter.kind === "tag") return `#/tag/${encodeURIComponent(filter.tag)}`
  if (filter.kind === "set-aside") return "#/set-aside"
  if (filter.kind === "unsorted") return "#/unsorted"
  return "#/"
}

/**
 * The key for a choice: "<target>:<action>:<target revision>", with the board for a move. The same tap twice gives
 * the same key, so the inbox keeps one event. A choice made again after its earlier event was cancelled takes the
 * next free key, since a key names one event for good.
 */
export function choiceKey(pin: PinView, action: Action, board: string | undefined, events: InboxEvent[]): string {
  const base = `pins/${pin.id}:${action}:${pin.revision}${action === "move" && board ? `:${board}` : ""}`
  const taken = new Map(events.map((event) => [event.key, event]))
  let key = base
  for (let n = 2; taken.get(key)?.status === "cancelled"; n++) key = `${base}:${n}`
  return key
}

/** Whether `pending` and the new choice are two minds about the same pin: keep against set aside, or a move to another board. */
export function isChangeOfMind(pending: InboxEvent, action: Action, board: string | undefined): boolean {
  if (pending.action === "move" && action === "move") return pending.payload.board !== board
  const verdicts: Action[] = ["keep", "reject"]
  return verdicts.includes(pending.action) && verdicts.includes(action) && pending.action !== action
}

async function getJSON<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(path, { cache: "no-store" })
    if (!response.ok) return null
    return (await response.json()) as T
  } catch {
    return null
  }
}

/** True when the runtime serves this page; the static copy ships an api/health that says it is static. */
export async function probeLive(): Promise<boolean> {
  const health = await getJSON<{ mode?: string }>("./api/health")
  return health?.mode === "polling"
}

export interface Snapshot {
  pins: StoredRecord<PinBody>[]
  boards: StoredRecord<BoardBody>[]
  events: InboxEvent[]
}

export async function loadSnapshot(): Promise<Snapshot | null> {
  const [pins, boards, events] = await Promise.all([
    getJSON<StoredRecord<PinBody>[]>("./api/records/pins"),
    getJSON<StoredRecord<BoardBody>[]>("./api/records/boards"),
    getJSON<InboxEvent[]>("./api/inbox"),
  ])
  if (!pins || !boards || !events) return null
  return { pins, boards, events }
}

/** A request to the page's server; a server that does not answer is said in plain words. */
async function reach(path: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(path, init)
  } catch {
    throw new Error("The board could not be reached, so this choice did not go through.")
  }
}

export async function postChoice(body: {
  action: Action
  target: string
  payload: Record<string, string>
  key: string
}): Promise<InboxEvent> {
  const response = await reach("./api/inbox", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  const answer = await response.json().catch(() => ({ error: "The page's server sent no answer." }))
  if (!response.ok) throw new Error(answer.error ?? `The page's server answered ${response.status}.`)
  return answer as InboxEvent
}

export async function cancelChoice(id: string): Promise<InboxEvent | null> {
  const response = await reach(`./api/inbox/${encodeURIComponent(id)}/cancel`, { method: "POST" })
  if (!response.ok) return null
  return (await response.json()) as InboxEvent
}

/** Near-black on a light paint and near-white on a dark one, by the paint's perceived lightness. */
export function inkOn(hex: string): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return "#1c1917"
  const n = parseInt(m[1], 16)
  const lightness = (0.299 * ((n >> 16) & 255) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255
  return lightness > 0.6 ? "#1c1917" : "#fafaf9"
}
