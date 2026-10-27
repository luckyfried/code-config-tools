import type { Action, AppConfig, Day, InboxEvent, Recipe, ShoppingList, Status, StoredRecord } from "@/types"
import { COPY } from "@/lib/copy"

export const RECIPES = "recipes"
export const LISTS = "lists"
const ALL_DAYS: Day[] = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
export const DAY_SHORT: Record<Day, string> = { mon: "Mon", tue: "Tue", wed: "Wed", thu: "Thu", fri: "Fri", sat: "Sat", sun: "Sun" }
export const DAY_LONG: Record<Day, string> = {
  mon: "Monday", tue: "Tuesday", wed: "Wednesday", thu: "Thursday", fri: "Friday", sat: "Saturday", sun: "Sunday",
}

export type RecipeRecord = StoredRecord<Recipe>
export type ListRecord = StoredRecord<ShoppingList>

export interface Slot {
  day: Day
  date: Date
  today: boolean
}

// The seven days of the current week, starting Monday or Sunday as the inputs say.
export function weekSlots(weekStart: AppConfig["week_start"], now = new Date()): Slot[] {
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const mondayBased = (today.getDay() + 6) % 7
  const back = weekStart === "monday" ? mondayBased : today.getDay()
  const first = new Date(today)
  first.setDate(today.getDate() - back)
  const order = weekStart === "monday" ? ALL_DAYS : (["sun", ...ALL_DAYS.slice(0, 6)] as Day[])
  return order.map((day, n) => {
    const date = new Date(first)
    date.setDate(first.getDate() + n)
    return { day, date, today: date.getTime() === today.getTime() }
  })
}

export const target = (id: string) => `${RECIPES}/${id}`
export const choiceKey = (record: RecipeRecord, action: Action) => `${target(record.id)}:${action}:${record.revision}`
export const planKey = (ids: string[]) => `plan-week:${[...ids].sort().join(",")}`

export function sampleRecipes(config: AppConfig): RecipeRecord[] {
  return config.sample.recipes.map(({ id, ...body }) => ({ id, kind: RECIPES, revision: 1, at: body.found_at, body }))
}

export function sampleLists(config: AppConfig): ListRecord[] {
  return config.sample.lists.map(({ id, ...body }) => ({ id, kind: LISTS, revision: 1, at: body.made_at, body }))
}

export function sampleEvents(config: AppConfig): InboxEvent[] {
  return (config.sampleInbox ?? []).map((e, n) => ({
    id: `sample-${n}`,
    action: e.action,
    target: e.target ? target(e.target) : null,
    key: `sample-${n}`,
    at: e.at,
    payload: e.payload ?? {},
    status: e.status,
    result: e.result,
    error: e.error ?? null,
  }))
}

// The newest event on each target; the inbox comes oldest first.
export function latestByTarget(events: InboxEvent[]): Map<string, InboxEvent> {
  const latest = new Map<string, InboxEvent>()
  for (const e of events) if (e.target) latest.set(e.target, e)
  return latest
}

export const open = (e: InboxEvent | undefined) => !!e && (e.status === "pending" || e.status === "working")

// What a card shows: a choice the agent has not done yet shows as made, so the box answers the tap at once.
export function shownState(record: RecipeRecord, latest: InboxEvent | undefined): { status: Status; day: Day | null } {
  if (open(latest)) {
    if (latest!.action === "keep") return { status: "kept", day: null }
    if (latest!.action === "skip") return { status: "skipped", day: null }
    if (latest!.action === "week") return { status: "week", day: latest!.payload.day ?? null }
  }
  return { status: record.body.status, day: record.body.day }
}

// A card's line about its newest choice, in the words a person uses; a week card's badge carries the day.
export function stateWords(e: InboxEvent): string {
  switch (e.status) {
    case "pending":
      return COPY.stateNext
    case "working":
      return COPY.stateWorking
    case "completed":
      if (e.action === "week") {
        const day = e.payload.day ?? e.result?.day
        return day ? COPY.stateDinner.replace("{day}", DAY_LONG[day]) : COPY.filterWeek
      }
      return e.action === "keep" ? COPY.stateKept : COPY.stateSkipped
    case "failed":
      return e.error ? `${COPY.stateFailed}: ${e.error}` : COPY.stateFailed
    case "cancelled":
      return COPY.stateBack
  }
}

export function lastChecked(events: InboxEvent[]): Date | null {
  let newest: string | null = null
  for (const e of events) if (e.status === "completed" && (!newest || e.at > newest)) newest = e.at
  return newest ? new Date(newest) : null
}

export function whenWords(at: Date, now = new Date()): string {
  const time = at.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  const days = Math.round(
    (new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() -
      new Date(at.getFullYear(), at.getMonth(), at.getDate()).getTime()) /
      86400000,
  )
  if (days === 0) return `today at ${time}`
  if (days === 1) return `yesterday at ${time}`
  return `${at.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })} at ${time}`
}

export function newestList(lists: ListRecord[]): ListRecord | null {
  return lists.reduce<ListRecord | null>((best, l) => (!best || l.body.made_at > best.body.made_at ? l : best), null)
}

const FRACTIONS: [number, string][] = [[0.25, "¼"], [0.5, "½"], [0.75, "¾"], [1 / 3, "⅓"], [2 / 3, "⅔"]]

export function amountWords(amount: number | null): string {
  if (amount === null) return ""
  const whole = Math.floor(amount)
  const part = amount - whole
  if (part < 0.01) return String(whole)
  const frac = FRACTIONS.find(([v]) => Math.abs(v - part) < 0.04)
  if (!frac) return String(Math.round(amount * 10) / 10)
  return whole ? `${whole}${frac[1]}` : frac[1]
}

// An ingredient's amount for the household: grams and milliliters to the nearest 5, others to a quarter.
export function scaled(amount: number | null, unit: string | null, factor: number): number | null {
  if (amount === null) return null
  const v = amount * factor
  if (unit === "g" || unit === "ml") return Math.max(5, Math.round(v / 5) * 5)
  return Math.max(0.25, Math.round(v * 4) / 4)
}

export function quantity(amount: number | null, unit: string | null): string {
  const n = amountWords(amount)
  if (!n) return unit ?? ""
  return unit ? `${n} ${unit}` : n
}

export const shortDate = (d: Date) => d.toLocaleDateString("en-US", { month: "long", day: "numeric" })
