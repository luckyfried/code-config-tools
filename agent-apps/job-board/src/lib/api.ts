import type { Action, InboxEvent, StoredRecord } from "@/types"

async function json<T>(path: string, init?: RequestInit): Promise<{ ok: boolean; status: number; body: T | null }> {
  let res: Response
  try {
    res = await fetch(path, { cache: "no-store", ...init })
  } catch {
    throw new Error("This choice was not sent. Ask your agent to start the board, then tap again.")
  }
  let body: T | null = null
  if ((res.headers.get("Content-Type") ?? "").includes("application/json")) body = (await res.json()) as T
  return { ok: res.ok, status: res.status, body }
}

// The runtime answers ./api/health with its report; a plain static server answers with something else.
export async function isLive(): Promise<boolean> {
  try {
    const r = await json<{ mode?: string }>("./api/health")
    return r.ok && r.body?.mode === "polling"
  } catch {
    return false
  }
}

export async function loadRecords(kind: string): Promise<StoredRecord[]> {
  const r = await json<StoredRecord[]>(`./api/records/${kind}`)
  if (!r.ok || !Array.isArray(r.body)) throw new Error("The records could not be read.")
  return r.body
}

export async function loadInbox(): Promise<InboxEvent[]> {
  const r = await json<InboxEvent[]>("./api/inbox")
  if (!r.ok || !Array.isArray(r.body)) throw new Error("The inbox could not be read.")
  return r.body
}

export async function sendChoice(action: Action, target: string, key: string): Promise<InboxEvent> {
  const r = await json<InboxEvent & { error?: string }>("./api/inbox", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, target, payload: {}, key }),
  })
  if (!r.ok || !r.body) throw new Error(r.body?.error ?? `The choice was refused (${r.status}).`)
  return r.body
}

// Resolves to the cancelled event, or null when the event had already left pending.
export async function cancelChoice(id: string): Promise<InboxEvent | null> {
  const r = await json<InboxEvent>(`./api/inbox/${id}/cancel`, { method: "POST", body: "{}" })
  return r.ok ? r.body : null
}
