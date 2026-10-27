import type { ColorBy, Sport, Track } from "./types"

/** The largest index whose value is at or below `value` in an ascending array. */
export function indexAt(values: number[], value: number) {
  let lo = 0
  let hi = values.length - 1
  if (value <= values[0]) return 0
  if (value >= values[hi]) return hi
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (values[mid] <= value) lo = mid
    else hi = mid
  }
  return lo
}

export interface Sample {
  i: number
  lat: number
  lon: number
  d: number
  t: number
  ele: number | null
  v: number
  hr: number | null
}

function mix(a: number, b: number, f: number) {
  return a + (b - a) * f
}

function at(track: Track, i: number, f: number): Sample {
  const j = Math.min(track.t.length - 1, i + 1)
  const hrA = track.hr?.[i] ?? null
  const hrB = track.hr?.[j] ?? hrA
  return {
    i,
    lat: mix(track.lat[i], track.lat[j], f),
    lon: mix(track.lon[i], track.lon[j], f),
    d: mix(track.d[i], track.d[j], f),
    t: mix(track.t[i], track.t[j], f),
    ele: track.ele ? mix(track.ele[i], track.ele[j], f) : null,
    v: mix(track.v[i], track.v[j], f),
    hr: hrA == null ? null : mix(hrA, hrB ?? hrA, f),
  }
}

export function sampleAtTime(track: Track, t: number): Sample {
  const i = indexAt(track.t, t)
  const span = (track.t[i + 1] ?? track.t[i]) - track.t[i]
  return at(track, i, span > 0 ? Math.min(1, Math.max(0, (t - track.t[i]) / span)) : 0)
}

export function sampleAtDistance(track: Track, d: number): Sample {
  const i = indexAt(track.d, d)
  const span = (track.d[i + 1] ?? track.d[i]) - track.d[i]
  return at(track, i, span > 0 ? Math.min(1, Math.max(0, (d - track.d[i]) / span)) : 0)
}

export function timeAtDistance(track: Track, d: number) {
  return sampleAtDistance(track, d).t
}

/** Compass bearing in degrees from one point to another. */
export function bearing(lat1: number, lon1: number, lat2: number, lon2: number) {
  const p1 = (lat1 * Math.PI) / 180
  const p2 = (lat2 * Math.PI) / 180
  const dl = ((lon2 - lon1) * Math.PI) / 180
  const y = Math.sin(dl) * Math.cos(p2)
  const x = Math.cos(p1) * Math.sin(p2) - Math.sin(p1) * Math.cos(p2) * Math.cos(dl)
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360
}

/** The heading over the stretch of track from `behind` meters back to `ahead` meters on. */
export function headingAt(track: Track, d: number, behind: number, ahead: number) {
  const total = track.d[track.d.length - 1]
  const a = sampleAtDistance(track, Math.max(0, d - behind))
  const b = sampleAtDistance(track, Math.min(total, d + ahead))
  if (b.d - a.d < 1) return null
  return bearing(a.lat, a.lon, b.lat, b.lon)
}

/** The track's points from distance `from` to `to`, as [lon, lat] pairs. */
export function stretch(track: Track, from: number, to: number): [number, number][] {
  const a = sampleAtDistance(track, Math.max(0, from))
  const b = sampleAtDistance(track, to)
  const out: [number, number][] = [[a.lon, a.lat]]
  for (let i = a.i + 1; i <= b.i; i++) out.push([track.lon[i], track.lat[i]])
  out.push([b.lon, b.lat])
  return out
}

/** The value that colors the track at each point, with gaps filled from the nearest reading. */
export function metricValues(track: Track, colorBy: ColorBy): number[] | null {
  if (colorBy === "heart") {
    if (!track.hr) return null
    const out: number[] = []
    let last = track.hr.find((h) => h != null) ?? 0
    for (const h of track.hr) {
      if (h != null) last = h
      out.push(last)
    }
    return out
  }
  if (colorBy === "elevation") return track.ele
  return track.v
}

/** The 5th and 95th percentiles, so one stop at a gate does not wash out the rest of the colors. */
export function spread(values: number[]): [number, number] {
  const sorted = values.filter(Number.isFinite).toSorted((a, b) => a - b)
  if (sorted.length === 0) return [0, 1]
  const lo = sorted[Math.floor(sorted.length * 0.05)]
  const hi = sorted[Math.floor(sorted.length * 0.95)]
  return hi - lo < 1e-6 ? [lo - 1, hi + 1] : [lo, hi]
}

/** Which metric the track is colored by, falling back to pace when the file has no reading for it. */
export function effectiveColorBy(track: Track, wanted: ColorBy): ColorBy {
  if (wanted === "heart" && !track.hr) return "pace"
  if (wanted === "elevation" && !track.ele) return "pace"
  return wanted
}

export function totalDistance(track: Track) {
  return track.d[track.d.length - 1]
}

export function totalTime(track: Track) {
  return track.t[track.t.length - 1]
}

/** Slower than this, in meters a second, counts as stopped: the same rule the run's moving time uses. */
const MOVING_FLOOR: Record<Sport, number> = { run: 0.6, hike: 0.3, ride: 1.2 }
const moving = new WeakMap<Track, Float64Array>()

/** Seconds spent moving from the start to each point. */
function movingSeconds(track: Track) {
  let out = moving.get(track)
  if (out) return out
  out = new Float64Array(track.t.length)
  const floor = MOVING_FLOOR[track.sport]
  for (let i = 1; i < track.t.length; i++) {
    const dt = track.t[i] - track.t[i - 1]
    const going = !track.has.time || (dt > 0 && dt < 60 && (track.d[i] - track.d[i - 1]) / dt >= floor)
    out[i] = out[i - 1] + (going ? dt : 0)
  }
  moving.set(track, out)
  return out
}

/** The moving time at `t` seconds into the activity: the clock with the stops taken out. */
export function movingTimeAt(track: Track, t: number) {
  const m = movingSeconds(track)
  const i = indexAt(track.t, t)
  const j = Math.min(track.t.length - 1, i + 1)
  if (j === i || m[j] === m[i]) return m[i]
  return m[i] + Math.min(track.t[j] - track.t[i], Math.max(0, t - track.t[i]))
}
