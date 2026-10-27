export type Action = "later" | "skip" | "more" | "deeper"
export type Status = "new" | "later" | "skipped"
export type EventState = "pending" | "working" | "completed" | "failed" | "cancelled"

export interface Coverage {
  headline: string
  source: string
  link: string
}

export interface Deep {
  paragraphs: string[]
  coverage: Coverage[]
  at: string
}

export interface Article {
  id: string
  headline: string
  source: string
  link: string
  image: string
  color: string
  topic: string
  summary: string[]
  minutes: number
  published_at: string
  found_at: string
  status: Status
  like: string | null
  deep: Deep | null
  agent_notes: string[]
  /** The stored record's revision; the sample's stories carry 1. */
  revision: number
}

export interface Topic {
  id: string
  name: string
  color: string
}

export interface InboxEvent {
  id: string
  action: Action
  target: string
  status: EventState
  at: string
  result: Record<string, unknown> | null
  error?: string | null
  key?: string
}

export interface StoredRecord<T> {
  id: string
  kind: string
  revision: number
  at: string
  body: T
}

export interface AppConfig {
  name: string
  topics: Topic[]
  sources?: { favor?: string[]; leave_out?: string[] }
  per_day?: number
  theme?: string
  sample?: {
    articles?: Omit<Article, "revision">[]
    inbox?: InboxEvent[]
    landing?: { id: string; deep: Deep } | null
  }
}

declare global {
  interface Window {
    __APP_CONFIG__?: AppConfig
  }
}
