export type MetricFormat = "number" | "currency" | "percent" | "duration"
export type TileSize = "1x1" | "2x1" | "2x2"

export type Point = { date: string; value: number }

export type Metric = {
  id: string
  label: string
  unit?: string
  format: MetricFormat
  higherIsBetter: boolean
  size: TileSize
  goal?: number | null
  history: Point[]
}

export type Group = { label: string; metrics: Metric[] }

/** Every word on the wall that is not a number or a label from the inputs. Each can be replaced under "copy". */
export const DEFAULT_COPY = {
  tvMode: "TV mode",
  leaveTvMode: "Leave TV mode",
  tvHint: "Press F for TV mode and Esc to leave it",
  refreshed: "Refreshed",
  notRefreshed: "Not refreshed yet",
  since: "Since",
  goal: "Goal",
  goalMet: "Goal met",
  firstReading: "First reading",
  noReadings: "No readings",
  readings: "readings",
  everyReading: "Every reading",
  date: "Date",
  reading: "Reading",
  change: "Change",
  first: "First",
  emptyTitle: "This wall has no numbers yet",
  emptyText: "Ask your agent to add the four to twelve numbers you care about, and where each one comes from.",
}

export type Copy = typeof DEFAULT_COPY

export type WallConfig = {
  title: string
  refreshedAt?: string
  theme?: string
  copy: Copy
  groups: Group[]
}

type RawConfig = Omit<WallConfig, "copy"> & { copy?: Partial<Copy> }

declare global {
  interface Window {
    __APP_CONFIG__?: RawConfig
  }
}

const EMPTY: RawConfig = { title: "Numbers Wall", groups: [] }

/** config.js is a classic script that runs before the bundle, so the config is there on first render. */
export function readConfig(): WallConfig {
  const config = window.__APP_CONFIG__ ?? EMPTY
  return {
    ...config,
    copy: { ...DEFAULT_COPY, ...config.copy },
    groups: config.groups.map((group) => ({
      ...group,
      metrics: group.metrics.map((metric) => ({
        ...metric,
        history: metric.history.toSorted((a, b) => a.date.localeCompare(b.date)),
      })),
    })),
  }
}
