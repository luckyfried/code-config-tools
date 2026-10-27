import type { ColorBy, Units } from "./types"

export interface AppConfig {
  athlete: string
  activities: string
  units: Units
  colorBy: ColorBy
  theme: string
  labels: boolean
  strava: boolean
}

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<AppConfig>
  }
}

const fallback: AppConfig = {
  athlete: "",
  activities: "media",
  units: "km",
  colorBy: "pace",
  theme: "topo",
  labels: false,
  strava: false,
}

function read(): AppConfig {
  const given = window.__APP_CONFIG__ ?? {}
  const merged = { ...fallback, ...given }
  if (merged.units !== "km" && merged.units !== "mi") merged.units = "km"
  if (!["pace", "heart", "elevation"].includes(merged.colorBy)) merged.colorBy = "pace"
  return merged
}

export const config = read()

/** Every key this app keeps in the browser starts with the app's name, since several apps can share one address. */
export const storageKey = (name: string) => `trail-replay:${name}`
