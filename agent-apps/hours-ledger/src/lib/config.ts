// The inputs run.py writes into config.js as window.__APP_CONFIG__, read once at load.

export type Client = { id: string; name: string; rate: number; color: string }

export type AppConfig = {
  name: string
  currency: string
  clients: Client[]
  rounding: number
  weekStart: "mon" | "sun"
  theme: "studio" | "ledger" | "auto"
  sample: boolean
  statementNote: string
}

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
  }
}

const raw = window.__APP_CONFIG__ ?? {}

export const config: AppConfig = {
  name: raw.name ?? "Your studio",
  currency: raw.currency ?? "USD",
  clients: raw.clients?.length ? raw.clients : [{ id: "client", name: "Client", rate: 100, color: "#3f6fa8" }],
  rounding: raw.rounding ?? 15,
  weekStart: raw.weekStart === "sun" ? "sun" : "mon",
  theme: raw.theme ?? "auto",
  sample: raw.sample ?? false,
  statementNote: raw.statementNote ?? "",
}

const byId = new Map(config.clients.map((c) => [c.id, c]))

export function clientById(id: string): Client {
  return byId.get(id) ?? { id, name: "Removed client", rate: 0, color: "#888888" }
}

// The client's hue set at the theme's lightness and chroma, so every client sits in the one palette.
export function clientColor(id: string): string {
  return `oklch(from ${clientById(id).color} calc(var(--client-l) + (l - 0.62) * 0.35) min(c, var(--client-c)) h)`
}

export const money = new Intl.NumberFormat(undefined, { style: "currency", currency: config.currency })

export const weekStartsOn: 0 | 1 = config.weekStart === "sun" ? 0 : 1
