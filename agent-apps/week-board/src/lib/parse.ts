import { addDays, getDay } from "date-fns"
import { LATER, fromKey, toKey, type DayKey, type WeekView } from "./dates"

/** The fixed words the Add field understands at the end of a line. Index 0 is Sunday. */
const DAY_WORDS: Record<string, number> = {
  sun: 0, sunday: 0,
  mon: 1, monday: 1,
  tue: 2, tues: 2, tuesday: 2,
  wed: 3, weds: 3, wednesday: 3,
  thu: 4, thur: 4, thurs: 4, thursday: 4,
  fri: 5, friday: 5,
  sat: 6, saturday: 6,
}

export type Target = DayKey | typeof LATER

export interface Parsed {
  title: string
  /** The column the word named, or null when the line ends in no day word. */
  target: Target | null
  word: string | null
}

/**
 * Reads a trailing day word: "call the bank fri", "pay rent tomorrow", "repaint the fence later".
 * A day that has already passed this week, or one the board does not show, goes to Later when the
 * Later rail is on and to today when it is off.
 */
export function parseLine(line: string, view: WeekView, laterOn: boolean): Parsed {
  const trimmed = line.trim().replace(/\s+/g, " ")
  const m = /^(.*\S)\s+(\S+)$/.exec(trimmed)
  if (!m) return { title: trimmed, target: null, word: null }
  const [, rest, raw] = m
  const word = raw.toLowerCase().replace(/[.,!]$/, "")
  const fallback: Target = laterOn ? LATER : view.anchor

  if (word === "today") return { title: rest, target: view.anchor, word: raw }
  if (word === "later" || word === "someday") return { title: rest, target: laterOn ? LATER : view.anchor, word: raw }
  if (word === "tomorrow" || word === "tmrw") {
    const k = toKey(addDays(fromKey(view.today), 1))
    return { title: rest, target: view.days.includes(k) ? k : fallback, word: raw }
  }
  if (word in DAY_WORDS) {
    const want = DAY_WORDS[word]
    const k = view.days.find((d) => getDay(fromKey(d)) === want)
    if (!k || k < view.anchor) return { title: rest, target: fallback, word: raw }
    return { title: rest, target: k, word: raw }
  }
  return { title: trimmed, target: null, word: null }
}
