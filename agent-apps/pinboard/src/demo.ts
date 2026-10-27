import type { Dispatch, SetStateAction } from "react"
import type { Snapshot } from "@/lib/data"
import { flyTo } from "@/lib/motion"
import type { Action, AppConfig, InboxEvent, PinBody, StoredRecord } from "@/types"

interface DemoHands {
  setSnapshot: Dispatch<SetStateAction<Snapshot>>
  setFolding: Dispatch<SetStateAction<Set<string>>>
  cards: Map<string, HTMLElement>
  shelves: Map<string, HTMLElement>
  isStopped: () => boolean
}

const wait = (ms: number) => new Promise((done) => window.setTimeout(done, ms))

function event(action: Action, pin: string, status: InboxEvent["status"], extra: Partial<InboxEvent> = {}): InboxEvent {
  return {
    id: `sample-${action}-${pin}`,
    action,
    target: `pins/${pin}`,
    target_revision: 1,
    key: `pins/${pin}:${action}:1`,
    at: new Date().toISOString(),
    payload: {},
    status,
    result: null,
    error: null,
    attempts: status === "pending" ? 0 : 1,
    ...extra,
  }
}

function withEvent(snap: Snapshot, next: InboxEvent): Snapshot {
  return { ...snap, events: [...snap.events.filter((e) => e.id !== next.id), next] }
}

function withPin(snap: Snapshot, id: string, change: Partial<PinBody>): Snapshot {
  return {
    ...snap,
    pins: snap.pins.map((record) => (record.id === id ? { ...record, revision: record.revision + 1, body: { ...record.body, ...change } } : record)),
  }
}

/**
 * The sample wall plays one round of the loop once, so the page opened without its server still shows what a tap
 * does: a keep, a set aside, a move to a board, and a "more like this" whose finds arrive beside the pin that asked.
 */
export async function runSampleDemo(config: AppConfig, hands: DemoHands) {
  const { setSnapshot, setFolding, cards, shelves, isStopped } = hands
  const has = (id: string) => config.sample.some((pin) => pin.id === id)
  const beat = async (ms: number) => {
    await wait(ms)
    return !isStopped()
  }

  if (has("philosophers-path") && (await beat(3000))) {
    setSnapshot((s) => withEvent(s, event("keep", "philosophers-path", "pending")))
    if (!(await beat(700))) return
    setSnapshot((s) =>
      withEvent(withPin(s, "philosophers-path", { status: "kept" }), event("keep", "philosophers-path", "completed", { result: { said: "Kept" } })),
    )
  }

  if (has("oak-shelving") && (await beat(600))) {
    setFolding((now) => new Set(now).add("oak-shelving"))
    setSnapshot((s) => withEvent(s, event("reject", "oak-shelving", "pending")))
    if (!(await beat(700))) return
    setSnapshot((s) =>
      withEvent(withPin(s, "oak-shelving", { status: "rejected" }), event("reject", "oak-shelving", "completed", { result: { said: "Set aside" } })),
    )
  }

  if (has("brass-pendants") && (await beat(600))) {
    const card = cards.get("brass-pendants")
    if (card) await flyTo(card, shelves.get("kitchen") ?? null)
    if (isStopped()) return
    setSnapshot((s) =>
      withEvent(
        withPin(s, "brass-pendants", { board: "kitchen" }),
        event("move", "brass-pendants", "completed", { payload: { board: "kitchen", name: "Kitchen" }, result: { said: "Now on Kitchen" } }),
      ),
    )
  }

  const finds = config.sample.filter((pin) => pin.found_for)
  const asker = finds[0]?.found_for
  if (!asker || !(await beat(700))) return
  setSnapshot((s) => withEvent(s, event("find-more", asker, "working")))
  if (!(await beat(1700))) return
  const added = new Date().toISOString()
  setSnapshot((s) => {
    const arrived: StoredRecord<PinBody>[] = finds.map((pin) => ({ id: pin.id, kind: "pins", revision: 1, at: added, body: { ...pin, added } }))
    return withEvent({ ...s, pins: [...s.pins, ...arrived] }, event("find-more", asker, "completed", { at: s.events.find((e) => e.id === `sample-find-more-${asker}`)?.at ?? added, result: { next: "find more like this pin" } }))
  })
}
