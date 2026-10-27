// The page reads its tournament from window.__APP_CONFIG__, which run.py writes into config.js from the inputs file.

export type ResultInput = { match: string; winner: string; score?: string }

export type Copy = {
  bracket: string
  picks: string
  results: string
  pool: string
  bigScreen: string
  leaveBigScreen: string
  replay: string
  wholeBracket: string
  export: string
  import: string
  champion: string
  upset: string
  bye: string
  points: string
  correct: string
  maxPossible: string
  championPick: string
  picksFor: string
  passTo: string
  picksDone: string
  resultsHint: string
  picksHint: string
  scorePlaceholder: string
  clear: string
  waiting: string
  imported: string
  importFailed: string
  noPeople: string
}

export type AppConfig = {
  title: string
  entrants: string[]
  people: string[]
  results: ResultInput[]
  picks: Record<string, Record<string, string>>
  colors: Record<string, string>
  copy: Copy
}

export const DEFAULT_COPY: Copy = {
  bracket: "Bracket",
  picks: "Picks",
  results: "Results",
  pool: "Pool",
  bigScreen: "Big screen",
  leaveBigScreen: "Leave big screen",
  replay: "Replay",
  wholeBracket: "Whole bracket",
  export: "Export",
  import: "Import",
  champion: "Champions",
  upset: "Upset",
  bye: "Bye",
  points: "Points",
  correct: "Correct",
  maxPossible: "Can still reach",
  championPick: "Champion pick",
  picksFor: "Picks for",
  passTo: "Pass to",
  picksDone: "Every pick is in",
  resultsHint: "Tap the winner of each match, then add the score.",
  picksHint: "Pick a winner in every match. Arrow keys move between matches, Enter picks.",
  scorePlaceholder: "Score",
  clear: "Clear",
  waiting: "Waiting on earlier matches",
  imported: "Picks and results loaded from the file.",
  importFailed: "That file is not a bracket export from this page.",
  noPeople: "Add people to the inputs file to start a pool.",
}

// Fallback entrant colors, used in seed order when the inputs name no color for an entrant.
const PALETTE = [
  "#e4572e", "#2e86ab", "#f3a712", "#29bf12", "#a23b72", "#3f88c5", "#ff8c42", "#6a4c93",
  "#00a6a6", "#d7263d", "#8ac926", "#1982c4", "#ffca3a", "#6d597a", "#ef476f", "#118ab2",
]

type RawConfig = Partial<Omit<AppConfig, "copy">> & { copy?: Partial<Copy> }

export function readConfig(): AppConfig {
  const raw = ((window as unknown as { __APP_CONFIG__?: RawConfig }).__APP_CONFIG__ ?? {}) as RawConfig
  const entrants = Array.isArray(raw.entrants) ? raw.entrants.filter((e) => typeof e === "string") : []
  const colors: Record<string, string> = {}
  entrants.forEach((name, i) => {
    colors[name] = raw.colors?.[name] ?? PALETTE[i % PALETTE.length]
  })
  return {
    title: raw.title ?? "Tournament",
    entrants,
    people: Array.isArray(raw.people) ? raw.people : [],
    results: Array.isArray(raw.results) ? raw.results : [],
    picks: raw.picks && typeof raw.picks === "object" ? raw.picks : {},
    colors,
    copy: { ...DEFAULT_COPY, ...(raw.copy ?? {}) },
  }
}
