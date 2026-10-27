// Every word on the page that is not a recipe's own. The inputs file's "copy" object replaces any of them by key;
// "{name}" in title is the inputs' name.
export const COPY = {
  title: "{name}’s recipe box",
  titleNoName: "Your recipe box",
  filterBox: "The box",
  filterNew: "New",
  filterKept: "Kept",
  filterWeek: "This week",
  filterSkipped: "Skipped",
  agentMaking: "Your agent is making the list",
  agentChecked: "Your agent last checked",
  agentAsk: "The agent checks when you ask.",
  sampleWeek: "Sample week",
  stateNext: "Your agent will look at this next",
  stateWorking: "Your agent is on it",
  stateKept: "Kept to cook again",
  stateDinner: "{day} dinner",
  stateSkipped: "Out of the box",
  stateBack: "You took this back",
  stateFailed: "Your agent couldn't do this",
  keep: "Keep",
  skip: "Skip",
  thisWeek: "This week",
  planWeek: "Plan the week",
  making: "Making your list",
  list: "List",
  noList: "No list yet",
  openDay: "Open",
  pickFirst: "Put a recipe on a day first.",
  emptyBox: "Your box is empty.",
  emptyBoxHint: "Ask your agent to find recipes for you; each one lands here as a card.",
  emptyFilter: "Nothing here yet.",
  emptyFilterHint: "Recipes you choose this way show up here.",
  fullRecipe: "The full recipe",
}

export type CopyKey = keyof typeof COPY

export function setCopy(words: Record<string, string> | undefined) {
  for (const [k, v] of Object.entries(words ?? {})) if (k in COPY && typeof v === "string") COPY[k as CopyKey] = v
}
