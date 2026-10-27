export type Status = "new" | "kept" | "rejected"
export type Action = "keep" | "reject" | "move" | "find-more"
export type EventState = "pending" | "working" | "completed" | "failed" | "cancelled"

export interface PinBody {
  id: string
  title: string
  image: string
  source: string
  note: string
  tags: string[]
  board: string | null
  color: string
  status: Status
  agent_notes: string[]
  found_for?: string | null
  added?: string
}

export interface BoardBody {
  id: string
  name: string
}

export interface StoredRecord<T> {
  id: string
  kind: string
  revision: number
  at: string
  body: T
}

export interface InboxEvent {
  id: string
  action: Action
  target: string | null
  target_revision: number | null
  key: string
  at: string
  payload: { board?: string; name?: string }
  status: EventState
  result: { said?: string; next?: string; board?: string; status?: Status; checked_at?: string } | null
  error: string | null
  attempts: number
}

export interface AppConfig {
  name: string
  boards: string[]
  theme: string
  sample: PinBody[]
}

export type Mode = "loading" | "live" | "static"

/** A pin as the wall draws it: the stored record with the person's pending choice laid over it. */
export interface PinView {
  id: string
  revision: number
  body: PinBody
  status: Status
  board: string | null
  latest: InboxEvent | null
  history: InboxEvent[]
  asking: boolean
  /** How many pins were found for this one. */
  found: number
}

export type Filter = { kind: "all" } | { kind: "board"; id: string } | { kind: "tag"; tag: string } | { kind: "set-aside" } | { kind: "unsorted" }

declare global {
  interface Window {
    __APP_CONFIG__?: AppConfig
  }
}
