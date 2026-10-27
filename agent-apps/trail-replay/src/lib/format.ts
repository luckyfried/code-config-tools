import type { Sport, Units } from "./types"

const KM = 1000
const MI = 1609.344
const FT = 3.28084

export const unitLength = (units: Units) => (units === "km" ? KM : MI)
export const distanceUnit = (units: Units) => (units === "km" ? "km" : "mi")
export const heightUnit = (units: Units) => (units === "km" ? "m" : "ft")

export function distanceValue(meters: number, units: Units) {
  return meters / unitLength(units)
}

export function formatDistance(meters: number, units: Units, digits = 2) {
  return distanceValue(meters, units).toFixed(digits)
}

export function heightValue(meters: number, units: Units) {
  return units === "km" ? meters : meters * FT
}

/** One formatter for every whole number on the page; making one per call is slow enough to cost frames. */
const WHOLE = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 })

export const formatWhole = (n: number) => WHOLE.format(Math.round(n))

export function formatHeight(meters: number, units: Units) {
  return formatWhole(heightValue(meters, units))
}

export function formatDuration(seconds: number, alwaysHours = false) {
  const s = Math.max(0, Math.round(seconds))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  if (h > 0 || alwaysHours) return `${h}:${String(m).padStart(2, "0")}:${String(r).padStart(2, "0")}`
  return `${m}:${String(r).padStart(2, "0")}`
}

/** Rides read as speed; runs and hikes as pace. */
export const usesSpeed = (sport: Sport) => sport === "ride"

export function paceLabel(sport: Sport, units: Units) {
  return usesSpeed(sport) ? (units === "km" ? "km/h" : "mph") : `/${distanceUnit(units)}`
}

export function paceName(sport: Sport) {
  return usesSpeed(sport) ? "Speed" : "Pace"
}

/** Pace in seconds per unit, or speed in units per hour, from meters per second. */
export function paceValue(speed: number, sport: Sport, units: Units) {
  if (usesSpeed(sport)) return (speed * 3600) / unitLength(units)
  return speed > 0.05 ? unitLength(units) / speed : Number.POSITIVE_INFINITY
}

export function formatPace(speed: number, sport: Sport, units: Units) {
  const value = paceValue(speed, sport, units)
  if (usesSpeed(sport)) return value.toFixed(1)
  if (!Number.isFinite(value) || value > 60 * 60) return "–"
  return formatDuration(value)
}

export function sportName(sport: Sport) {
  return sport === "ride" ? "Ride" : sport === "hike" ? "Hike" : "Run"
}

export function formatDate(iso: string | null) {
  if (!iso) return "Route"
  const date = new Date(iso)
  return date.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })
}

export function formatShortDate(iso: string | null) {
  if (!iso) return "Route"
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

export function formatTimeOfDay(iso: string | null) {
  if (!iso) return ""
  return new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
}

export function formatCoordinate(lat: number, lon: number) {
  const ns = lat >= 0 ? "N" : "S"
  const ew = lon >= 0 ? "E" : "W"
  return `${Math.abs(lat).toFixed(4)}° ${ns}, ${Math.abs(lon).toFixed(4)}° ${ew}`
}
