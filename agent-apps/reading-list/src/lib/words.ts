// Times and choices in the words the page shows.

import type { Action, InboxEvent } from "@/types"

const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString()

/** "8:05 AM" today, "yesterday at 8:05 AM", or "Oct 20 at 8:05 AM". */
export function clock(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  const now = new Date()
  if (sameDay(d, now)) return time
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (sameDay(d, yesterday)) return `yesterday at ${time}`
  return `${d.toLocaleDateString("en-US", { month: "short", day: "numeric" })} at ${time}`
}

export const today = () =>
  new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })

const ASKED: Record<Action, string> = {
  later: "Saved for later",
  skip: "Skipped",
  more: "You asked for more like this",
  deeper: "You asked for a longer brief",
}

const DONE: Record<Action, string> = {
  later: "Saved for later",
  skip: "Skipped",
  more: "Your agent is finding more like this",
  deeper: "Your agent is writing the brief",
}

/** A choice and where the agent is with it, as one sentence. */
export function choiceSays(e: InboxEvent): string {
  switch (e.status) {
    case "pending":
      return `${ASKED[e.action]}. Your agent sees it next time it checks.`
    case "working":
      return `${ASKED[e.action]}. Your agent is on it now.`
    case "completed":
      return `${DONE[e.action]}.`
    case "failed":
      return `${ASKED[e.action]}, but your agent couldn’t do it${e.error ? `: ${e.error}` : "."}`
    default:
      return `${ASKED[e.action]}, then you took it back.`
  }
}

/** "at 8:05 AM", "yesterday at 8:05 AM", or "on Oct 20 at 8:05 AM", to follow a verb. */
export function when(iso: string): string {
  const said = clock(iso)
  if (said.startsWith("yesterday")) return said
  return /^\d/.test(said) ? `at ${said}` : `on ${said}`
}
