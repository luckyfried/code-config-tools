export type Segment =
  | { kind: "text"; text: string }
  | { kind: "time"; text: string; ms: number; index: number }

const NUMBER = String.raw`\d+(?:\.\d+)?(?:\s?[½¼¾⅓⅔])?|[½¼¾⅓⅔]`
const UNIT = String.raw`hours?|hrs?|minutes?|mins?|seconds?|secs?`
const SECOND_PART = String.raw`(?:\s*(?:and\s+)?(${NUMBER})\s*(minutes?|mins?))?`
// A number always comes first, so "minced" or "a minute" never becomes a timer.
const DURATION = new RegExp(
  String.raw`(?<![\w.])(${NUMBER})(?:\s*(?:-|–|to)\s*(?:${NUMBER}))?\s*(${UNIT})\b${SECOND_PART}`,
  "gi",
)

const GLYPHS: Record<string, number> = { "½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3 }

function numberOf(text: string) {
  const glyph = text.match(/[½¼¾⅓⅔]/)
  const digits = text.replace(/[½¼¾⅓⅔]/, "").trim()
  return (digits ? Number(digits) : 0) + (glyph ? GLYPHS[glyph[0]] : 0)
}

function msOf(amount: number, unit: string) {
  const u = unit.toLowerCase()
  if (u.startsWith("h")) return amount * 3_600_000
  if (u.startsWith("m")) return amount * 60_000
  return amount * 1000
}

/** A step's text, split into plain runs and durations a timer can start from. */
export function splitDurations(text: string): Segment[] {
  const segments: Segment[] = []
  let last = 0
  let index = 0
  for (const match of text.matchAll(DURATION)) {
    const start = match.index ?? 0
    if (start > last) segments.push({ kind: "text", text: text.slice(last, start) })
    let ms = msOf(numberOf(match[1]), match[2])
    if (match[3] && match[4]) ms += msOf(numberOf(match[3]), match[4])
    if (ms > 0) {
      segments.push({ kind: "time", text: match[0], ms, index })
      index += 1
    } else {
      segments.push({ kind: "text", text: match[0] })
    }
    last = start + match[0].length
  }
  if (last < text.length) segments.push({ kind: "text", text: text.slice(last) })
  return segments
}

export function firstDuration(text: string) {
  return splitDurations(text).find((segment) => segment.kind === "time") as
    | Extract<Segment, { kind: "time" }>
    | undefined
}

export function clock(ms: number) {
  const total = Math.max(0, Math.ceil(ms / 1000))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  const pad = (n: number) => String(n).padStart(2, "0")
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`
}

export function minutesText(minutes: number) {
  if (minutes < 60) return `${minutes} min`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m === 0 ? `${h} hr` : `${h} hr ${m}`
}
