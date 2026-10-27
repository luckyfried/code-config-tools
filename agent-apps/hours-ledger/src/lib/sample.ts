import { addDays, startOfDay } from "date-fns"
import { config } from "./config"
import type { Entry } from "./store"

// A sample of the last five weeks for the inputs' clients, written on the first open when "sample" is true, so the
// page shows a full week, a tinted month, and a timer already running. The same day always gets the same hours.

const NOTES = [
  "Kickoff call",
  "Homepage layout",
  "Type and color study",
  "Design check-in",
  "Component library",
  "Copy pass",
  "Prototype",
  "Revisions from feedback",
  "Handoff notes",
  "Icon set",
  "Packaging dieline",
  "Landing page build",
  "Accessibility fixes",
  "Weekly sync",
  "Photo selects",
  "Email templates",
]

function rng(seed: number) {
  let s = seed >>> 0
  return () => {
    s = (s + 0x6d2b79f5) >>> 0
    let t = s
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const MIN = 60_000

export function sampleEntries(now: number): Entry[] {
  const clients = config.clients
  const entries: Entry[] = []
  const today = startOfDay(now)
  let n = 0
  const id = () => `sample-${(n++).toString(36)}`

  for (let back = 36; back >= 1; back--) {
    const day = addDays(today, -back)
    const r = rng(Math.floor(day.getTime() / 86_400_000) * 7919)
    const weekend = day.getDay() === 0 || day.getDay() === 6
    if (weekend && r() > 0.25) continue
    const blocks = weekend ? 1 : 2 + Math.floor(r() * 3)
    let t = day.getTime() + (8.5 + r() * 1.5) * 60 * MIN
    for (let b = 0; b < blocks; b++) {
      const client = clients[Math.floor(r() * clients.length)]
      const length = (45 + Math.floor(r() * 160)) * MIN + Math.floor(r() * 50) * 1000
      entries.push({ id: id(), start: t, end: t + length, clientId: client.id, note: NOTES[Math.floor(r() * NOTES.length)] })
      t += length + (10 + Math.floor(r() * 50)) * MIN
    }
  }

  // Today: two finished blocks before the running timer, which started 38 minutes ago.
  const r = rng(Math.floor(today.getTime() / 86_400_000))
  const runStart = now - (38 * MIN + 17_000)
  const done: Entry[] = []
  let end = runStart - 12 * MIN
  for (let b = 0; b < 2; b++) {
    const length = (52 + Math.floor(r() * 70)) * MIN + 23_000
    const start = end - length
    if (start < today.getTime() + 6 * 60 * MIN) break
    const client = clients[(b + 1) % clients.length]
    done.push({ id: id(), start, end, clientId: client.id, note: NOTES[Math.floor(r() * NOTES.length)] })
    end = start - (15 + Math.floor(r() * 30)) * MIN
  }
  entries.push(...done.reverse())
  entries.push({ id: id(), start: Math.max(runStart, today.getTime()), end: null, clientId: clients[0].id, note: "Homepage layout" })
  return entries
}
