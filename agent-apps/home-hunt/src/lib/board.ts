import type { Action, AppConfig, Card, CompareRow, Home, InboxEvent, Status, StoredRecord } from "@/types"

export const KIND = "homes"
export const STATUS_ACTIONS: Action[] = ["yes", "no", "maybe"]
export const COLUMNS: Status[] = ["new", "yes", "maybe"]
export const COLUMN_NAMES: Record<Status, string> = { new: "New", yes: "Yes", maybe: "Maybe", no: "Passed" }

export const target = (id: string) => `${KIND}/${id}`
export const idOf = (t: string | null) => (t?.startsWith(`${KIND}/`) ? t.slice(KIND.length + 1) : null)

export function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID().replace(/-/g, "")
    : `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 10)}`
}

export function sampleRecords(config: AppConfig): StoredRecord[] {
  return (config.sample ?? []).map(({ id, ...body }) => ({ id, kind: KIND, revision: 1, at: body.found_at, body: body as Home }))
}

export function sampleEvents(config: AppConfig): InboxEvent[] {
  return (config.sampleInbox ?? []).map((e, n) => ({
    id: `sample-${n}`,
    action: e.action,
    target: target(e.target),
    key: `${target(e.target)}:${e.action}:sample-${n}`,
    at: e.at,
    payload: {},
    status: e.status,
    result: e.result ? { ...e.result, done_at: e.at } : null,
    error: null,
  }))
}

const live = (e: InboxEvent) => e.status === "pending" || e.status === "working"

// A status the person chose that the agent has not taken yet already moves the card; once taken, the record says it.
export function buildCards(records: StoredRecord[], events: InboxEvent[]): Card[] {
  const byTarget = new Map<string, InboxEvent[]>()
  for (const e of events) {
    const id = idOf(e.target)
    if (!id) continue
    const list = byTarget.get(id) ?? []
    list.push(e)
    byTarget.set(id, list)
  }
  return records.map((record) => {
    const own = (byTarget.get(record.id) ?? []).sort((a, b) => a.at.localeCompare(b.at))
    const statusEvents = own.filter((e) => STATUS_ACTIONS.includes(e.action) && e.status !== "cancelled" && e.status !== "failed")
    const lastStatus = statusEvents.at(-1)
    const shown = lastStatus && live(lastStatus) ? (lastStatus.action as Status) : record.body.status
    return {
      id: record.id,
      record,
      home: record.body,
      shown,
      latest: own.at(-1),
      events: own,
      movedAt: lastStatus?.at ?? record.body.found_at,
    }
  })
}

export function column(cards: Card[], status: Status): Card[] {
  return cards
    .filter((c) => c.shown === status)
    .sort((a, b) => b.movedAt.localeCompare(a.movedAt) || b.home.found_at.localeCompare(a.home.found_at))
}

export const statusKey = (card: Card, action: Action) => `${target(card.id)}:${action}:${card.record.revision}`

// The pending status choices a new status choice replaces.
export const replaced = (card: Card, action: Action) =>
  card.events.filter((e) => e.status === "pending" && STATUS_ACTIONS.includes(e.action) && e.action !== action)

const ACTION_WORDS: Record<Action, string> = { yes: "Yes", no: "No", maybe: "Maybe", note: "Note", ask: "Question" }

export function stateWords(e: InboxEvent): { label: string; detail: string | null; tone: "wait" | "work" | "done" | "fail" | "off" } {
  const what = ACTION_WORDS[e.action]
  if (e.status === "pending") return { label: `${what} · Waiting for your agent`, detail: null, tone: "wait" }
  if (e.status === "working") return { label: `${what} · Your agent is on it`, detail: null, tone: "work" }
  if (e.status === "cancelled") return { label: `${what} · Changed your mind`, detail: null, tone: "off" }
  if (e.status === "failed") return { label: `${what} · Your agent could not`, detail: e.error, tone: "fail" }
  const r = e.result ?? {}
  const detail = typeof r.note === "string" ? r.note : null
  return { label: `${what} · Your agent took it`, detail, tone: "done" }
}

export function lastChecked(events: InboxEvent[]): string | null {
  let best: string | null = null
  for (const e of events) {
    if (e.status !== "completed") continue
    const at = typeof e.result?.done_at === "string" ? e.result.done_at : e.at
    if (!best || at > best) best = at
  }
  return best
}

export function ago(iso: string, now = Date.now()): string {
  const s = Math.max(0, Math.round((now - Date.parse(iso)) / 1000))
  if (s < 60) return "just now"
  const m = Math.round(s / 60)
  if (m < 60) return `${m} min ago`
  const h = Math.round(m / 60)
  if (h < 24) return `${h} hr ago`
  const d = Math.round(h / 24)
  return d === 1 ? "yesterday" : `${d} days ago`
}

export function day(iso: string): string {
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

const moneyCache = new Map<string, Intl.NumberFormat>()
export function money(value: number, currency: string): string {
  const key = currency
  let f = moneyCache.get(key)
  if (!f) {
    try {
      f = new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 })
    } catch {
      f = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 })
    }
    moneyCache.set(key, f)
  }
  return f.format(Math.round(value))
}

export const unitWord = (units: string) => (units === "m2" ? "m²" : "sq ft")
export const number = (n: number) => n.toLocaleString("en-US", { maximumFractionDigits: 1 })

export function priceLabel(home: Home, currency: string) {
  return `${money(home.price, currency)}${home.period === "month" ? "/mo" : ""}`
}

export function perArea(home: Home): number | null {
  return home.area && home.area > 0 ? home.price / home.area : null
}

export function commuteMinutes(text: string | null): number | null {
  if (!text) return null
  const h = /(\d+(?:\.\d+)?)\s*(?:h|hr|hour)/i.exec(text)
  const m = /(\d+)\s*min/i.exec(text)
  if (!h && !m) return null
  return (h ? Number(h[1]) * 60 : 0) + (m ? Number(m[1]) : 0)
}

export const ROW_NAMES = (units: string): Record<CompareRow, string> => ({
  price: "Price",
  price_per_area: `Price per ${unitWord(units)}`,
  rooms: "Bedrooms",
  baths: "Baths",
  area: "Floor area",
  commute: "Commute",
  place: "Neighborhood",
})

function rowValue(row: CompareRow, home: Home): number | null {
  switch (row) {
    case "price":
      return home.price
    case "price_per_area":
      return perArea(home)
    case "rooms":
      return home.rooms
    case "baths":
      return home.baths
    case "area":
      return home.area
    case "commute":
      return commuteMinutes(home.commute)
    default:
      return null
  }
}

const LOWER_WINS: CompareRow[] = ["price", "price_per_area", "commute"]

// The ids holding the best value in a row; an empty set when the row has no winner (all equal, or one value or none).
export function best(row: CompareRow, homes: { id: string; home: Home }[]): Set<string> {
  if (row === "place") return new Set()
  const vals = homes.map((h) => ({ id: h.id, v: rowValue(row, h.home) })).filter((x): x is { id: string; v: number } => x.v != null)
  if (vals.length < 2) return new Set()
  const pick = LOWER_WINS.includes(row) ? Math.min(...vals.map((x) => x.v)) : Math.max(...vals.map((x) => x.v))
  const winners = vals.filter((x) => Math.abs(x.v - pick) < 1e-9)
  if (winners.length === vals.length) return new Set()
  return new Set(winners.map((x) => x.id))
}

export function cell(row: CompareRow, home: Home, currency: string, units: string): string | null {
  switch (row) {
    case "price":
      return priceLabel(home, currency)
    case "price_per_area": {
      const p = perArea(home)
      return p == null ? null : money(p, currency)
    }
    case "rooms":
      return number(home.rooms)
    case "baths":
      return number(home.baths)
    case "area":
      return home.area == null ? null : `${number(home.area)} ${unitWord(units)}`
    case "commute":
      return home.commute
    case "place":
      return home.place || null
  }
}

export const hostOf = (link: string) => {
  try {
    return new URL(link).hostname.replace(/^www\./, "")
  } catch {
    return link
  }
}
