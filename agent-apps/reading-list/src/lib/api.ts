import type { Action, InboxEvent, StoredRecord } from "@/types"

interface Answer<T> {
  ok: boolean
  status: number
  body: T | null
}

async function call<T>(path: string, init?: RequestInit): Promise<Answer<T>> {
  let res: Response
  try {
    res = await fetch(path, { cache: "no-store", ...init })
  } catch {
    throw new Error("This choice was not sent. Ask your agent to start the page again, then tap once more.")
  }
  let body: T | null = null
  if ((res.headers.get("Content-Type") ?? "").includes("application/json")) body = (await res.json()) as T
  return { ok: res.ok, status: res.status, body }
}

// The runtime answers ./api/health with its report; a plain static server answers with the shipped stand-in file.
export async function isLive(): Promise<boolean> {
  try {
    const r = await call<{ mode?: string }>("./api/health")
    return r.ok && r.body?.mode === "polling"
  } catch {
    return false
  }
}

export async function loadRecords<T>(kind: string): Promise<StoredRecord<T>[]> {
  const r = await call<StoredRecord<T>[]>(`./api/records/${kind}`)
  if (!r.ok || !Array.isArray(r.body)) throw new Error(`The ${kind} could not be read.`)
  return r.body
}

export async function loadInbox(): Promise<InboxEvent[]> {
  const r = await call<InboxEvent[]>("./api/inbox")
  if (!r.ok || !Array.isArray(r.body)) throw new Error("Your choices could not be read.")
  return r.body
}

export async function sendChoice(action: Action, target: string, key: string): Promise<InboxEvent> {
  const r = await call<InboxEvent & { error?: string }>("./api/inbox", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, target, payload: {}, key }),
  })
  if (!r.ok || !r.body) throw new Error(r.body?.error ?? `The page refused this choice (${r.status}).`)
  return r.body
}

// Resolves to the cancelled event, or null when the agent had already taken it.
export async function cancelChoice(id: string): Promise<InboxEvent | null> {
  const r = await call<InboxEvent>(`./api/inbox/${id}/cancel`, { method: "POST", body: "{}" })
  return r.ok ? r.body : null
}
