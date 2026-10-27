import type { SeedDeal, Stage } from "@/lib/pipeline"

export interface AppConfig {
  name: string
  currency: string
  stages: Stage[]
  seedDeals: SeedDeal[]
  theme: string
}

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
  }
}

const STANDARD_STAGES: Stage[] = [
  { id: "lead", label: "Lead", probability: 10, color: "#5c5be2" },
  { id: "qualified", label: "Qualified", probability: 25, color: "#9e47db" },
  { id: "proposal", label: "Proposal", probability: 50, color: "#e73e9a" },
  { id: "negotiation", label: "Negotiation", probability: 70, color: "#f96c4a" },
  { id: "closing", label: "Closing", probability: 90, color: "#f9ad26" },
]

function read(): AppConfig {
  const raw = typeof window === "undefined" ? undefined : window.__APP_CONFIG__
  const stages = Array.isArray(raw?.stages) && raw.stages.length > 0 ? raw.stages : STANDARD_STAGES
  let currency = typeof raw?.currency === "string" ? raw.currency.toUpperCase() : "USD"
  try {
    new Intl.NumberFormat("en-US", { style: "currency", currency })
  } catch {
    currency = "USD"
  }
  return {
    name: typeof raw?.name === "string" && raw.name.trim() !== "" ? raw.name : "Deal Board",
    currency,
    stages: stages.map((stage) => ({ ...stage, probability: Math.min(100, Math.max(0, Math.round(stage.probability))) })),
    seedDeals: Array.isArray(raw?.seedDeals) ? raw.seedDeals : [],
    theme: typeof raw?.theme === "string" ? raw.theme : "auto",
  }
}

/** Read once at load from config.js, which run.py writes beside index.html. */
export const config: AppConfig = read()
