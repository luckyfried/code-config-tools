export type Status = "new" | "kept" | "skipped" | "week"
export type Day = "mon" | "tue" | "wed" | "thu" | "fri" | "sat" | "sun"
export type Action = "keep" | "skip" | "week" | "plan-week"
export type EventState = "pending" | "working" | "completed" | "failed" | "cancelled"

export interface Ingredient {
  name: string
  amount: number | null
  unit: string | null
  aisle: string
}

export interface Recipe {
  title: string
  image: string
  source: string
  color: string
  minutes: number
  servings: number
  ingredients: Ingredient[]
  steps: string[]
  tags: string[]
  why: string
  status: Status
  day: Day | null
  found_at: string
  agent_notes: string[]
}

export interface ListItem extends Ingredient {
  from: string[]
}

export interface ShoppingList {
  week_of: string
  recipes: string[]
  items: ListItem[]
  made_at: string
}

export interface StoredRecord<T> {
  id: string
  kind: string
  revision: number
  at: string
  body: T
}

export interface EventResult {
  note?: string
  list?: string
  items?: number
  next?: string
  status?: Status
  day?: Day | null
}

export interface InboxEvent {
  id: string
  action: Action
  target: string | null
  target_revision?: number | null
  key: string
  at: string
  payload: { day?: Day }
  status: EventState
  result: EventResult | null
  error: string | null
}

export interface SampleEvent {
  action: Action
  target: string | null
  status: EventState
  at: string
  result: EventResult | null
  error?: string | null
  payload?: { day?: Day }
}

export interface AppConfig {
  name: string
  ask: string
  household: number
  week_start: "monday" | "sunday"
  theme: string
  sample: { recipes: (Recipe & { id: string })[]; lists: (ShoppingList & { id: string })[] }
  sampleInbox?: SampleEvent[]
  copy?: Record<string, string>
}

declare global {
  interface Window {
    __APP_CONFIG__?: AppConfig
  }
}
