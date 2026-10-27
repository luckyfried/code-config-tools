import { format } from "date-fns"
import { clientById, config } from "./config"
import type { Entry } from "./store"
import { MINUTE, roundedMinutes } from "./time"

function download(name: string, type: string, text: string) {
  const url = URL.createObjectURL(new Blob([text], { type }))
  const a = document.createElement("a")
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

const cell = (v: string | number) => {
  const s = String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

// A header line, then one line per finished entry, oldest first.
export function entriesCsv(entries: Entry[], rounding: number): string {
  const head = ["date", "start", "end", "client", "client_id", "note", "minutes", "rounded_minutes", "rate", "amount"]
  const rows = entries
    .filter((e) => e.end !== null)
    .sort((a, b) => a.start - b.start)
    .map((e) => {
      const c = clientById(e.clientId)
      const ms = (e.end as number) - e.start
      const rounded = roundedMinutes(ms, rounding)
      return [
        format(e.start, "yyyy-MM-dd"),
        format(e.start, "HH:mm"),
        format(e.end as number, "HH:mm"),
        c.name,
        c.id,
        e.note,
        (ms / MINUTE).toFixed(2),
        rounded,
        c.rate,
        ((rounded / 60) * c.rate).toFixed(2),
      ]
    })
  return [head, ...rows].map((r) => r.map(cell).join(",")).join("\n") + "\n"
}

export function exportCsv(entries: Entry[], rounding: number) {
  download(`hours-ledger-${format(Date.now(), "yyyy-MM-dd")}.csv`, "text/csv", entriesCsv(entries, rounding))
}

export function exportJson(entries: Entry[], rounding: number) {
  const body = {
    name: config.name,
    currency: config.currency,
    rounding,
    clients: config.clients,
    entries: entries
      .slice()
      .sort((a, b) => a.start - b.start)
      .map((e) => ({ ...e, start: new Date(e.start).toISOString(), end: e.end === null ? null : new Date(e.end).toISOString() })),
  }
  download(`hours-ledger-${format(Date.now(), "yyyy-MM-dd")}.json`, "application/json", JSON.stringify(body, null, 2) + "\n")
}

// Reads a JSON export (or a bare list of entries); start and end may be ISO text or epoch milliseconds.
export function parseImport(text: string): Entry[] {
  const data = JSON.parse(text) as { entries?: unknown[] } | unknown[]
  const list = Array.isArray(data) ? data : (data.entries ?? [])
  const time = (v: unknown) => (typeof v === "number" ? v : typeof v === "string" ? Date.parse(v) : NaN)
  return list.flatMap((item) => {
    const e = item as Record<string, unknown>
    const start = time(e.start)
    const end = e.end === null ? null : time(e.end)
    if (!Number.isFinite(start) || (end !== null && !Number.isFinite(end)) || typeof e.clientId !== "string") return []
    const id = typeof e.id === "string" ? e.id : `import-${start}-${e.clientId}`
    return [{ id, start, end, clientId: e.clientId, note: typeof e.note === "string" ? e.note : "" }]
  })
}
