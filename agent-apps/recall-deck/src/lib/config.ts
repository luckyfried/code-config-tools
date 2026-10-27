// The deck and its defaults, from config.js, which run.py writes from <project>/recall-deck.inputs.json.

export interface Card {
  id: string
  front: string
  back: string
  tags: string[]
  hint?: string
}

export interface CardState {
  ease: number
  interval: number
  due: string
  reps: number
}

export interface DayLog {
  seen: number
  fresh: number
  again: number
}

export interface Progress {
  state: Record<string, CardState>
  log: Record<string, DayLog>
}

export interface AppConfig {
  deckName: string
  cards: Card[]
  newPerDay: number
  typing: boolean
  font: "sans" | "serif"
  progress: Progress
}

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
  }
}

const raw: Partial<AppConfig> = (typeof window !== "undefined" && window.__APP_CONFIG__) || {}

const cards = Array.isArray(raw.cards)
  ? raw.cards
      .filter((c) => c && typeof c.id === "string" && typeof c.front === "string" && typeof c.back === "string")
      .map((c) => ({ ...c, tags: Array.isArray(c.tags) ? c.tags.filter((t) => typeof t === "string") : [] }))
  : []

export const config: AppConfig = {
  deckName: typeof raw.deckName === "string" && raw.deckName ? raw.deckName : "Recall Deck",
  cards,
  newPerDay: Number.isInteger(raw.newPerDay) && raw.newPerDay! > 0 ? raw.newPerDay! : 10,
  typing: raw.typing === true,
  font: raw.font === "serif" ? "serif" : "sans",
  progress: {
    state: raw.progress && typeof raw.progress.state === "object" ? raw.progress.state : {},
    log: raw.progress && typeof raw.progress.log === "object" ? raw.progress.log : {},
  },
}

export const cardById = new Map(config.cards.map((c) => [c.id, c]))

export const allTags = [...new Set(config.cards.flatMap((c) => c.tags))].sort((a, b) => a.localeCompare(b))
