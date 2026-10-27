export type Status = "new" | "yes" | "no" | "maybe"
export type Action = "yes" | "no" | "maybe" | "note" | "ask"
export type EventState = "pending" | "working" | "completed" | "failed" | "cancelled"
export type CompareRow = "price" | "price_per_area" | "rooms" | "baths" | "area" | "commute" | "place"

export interface Checked {
  fact: string
  source: string
}

export interface Note {
  text: string
  at: string
}

export interface Question {
  question: string
  asked_at: string
  answer: string | null
  answered_at: string | null
}

export interface Home {
  title: string
  image: string
  photos: string[]
  source: string
  color: string
  price: number
  period: "sale" | "month"
  rooms: number
  baths: number
  area: number | null
  place: string
  commute: string | null
  checked: Checked[]
  status: Status
  notes: Note[]
  questions: Question[]
  found_at: string
  agent_notes: string[]
}

export interface StoredRecord {
  id: string
  kind: string
  revision: number
  at: string
  body: Home
}

export interface InboxEvent {
  id: string
  action: Action
  target: string | null
  key: string
  at: string
  payload: Record<string, unknown>
  status: EventState
  result: Record<string, unknown> | null
  error: string | null
}

export interface SampleEvent {
  action: Action
  target: string
  status: EventState
  at: string
  result?: Record<string, unknown>
}

export interface AppConfig {
  name: string
  ask: string
  currency: string
  units: "sqft" | "m2"
  compare_rows: CompareRow[]
  theme: string
  sample: (Home & { id: string })[]
  sampleInbox?: SampleEvent[]
}

export interface Card {
  id: string
  record: StoredRecord
  home: Home
  shown: Status
  latest: InboxEvent | undefined
  events: InboxEvent[]
  movedAt: string
}

declare global {
  interface Window {
    __APP_CONFIG__?: AppConfig
  }
}
