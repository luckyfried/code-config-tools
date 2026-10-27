export type Status = "new" | "yes" | "no" | "later"
export type Action = "yes" | "no" | "later" | "apply"
export type EventState = "pending" | "working" | "completed" | "failed" | "cancelled"

export interface Opportunity {
  id: string
  role: string
  company: string
  link: string
  location: string
  pay: string
  remote: boolean | null
  facts: string[]
  found_at: string
  status: Status
  agent_notes: string[]
  // When the agent recorded that the application went out.
  applied_at: string | null
}

export interface StoredRecord {
  id: string
  kind: string
  revision: number
  at: string
  body: Omit<Opportunity, "id"> & { id?: string }
}

export interface InboxEvent {
  id: string
  action: Action
  target: string | null
  target_revision: number | null
  key: string
  at: string
  payload: Record<string, unknown>
  status: EventState
  result: { note?: string; next?: string; done_at?: string } | null
  error: string | null
}

export interface SampleEvent {
  action: Action
  target: string
  status: EventState
  at: string
  result?: InboxEvent["result"]
}

export interface AppConfig {
  name: string
  ask: string
  columns: Status[]
  theme: string
  sample: Opportunity[]
  sampleInbox?: SampleEvent[]
}

export interface Card {
  record: StoredRecord
  job: Opportunity
  shown: Status
  latest: InboxEvent | null
  history: InboxEvent[]
}
