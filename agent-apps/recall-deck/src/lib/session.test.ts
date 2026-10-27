// Runs with: npm test
import { test } from "node:test"
import assert from "node:assert/strict"
import { readFileSync } from "node:fs"

const inputs = JSON.parse(readFileSync(new URL("../../inputs.example.json", import.meta.url), "utf8"))
Object.assign(globalThis, { window: { __APP_CONFIG__: inputs } })
const { buildQueue, forecast, graded, totals } = await import("./session.ts")

const now = "2026-10-27"
const saved = { state: inputs.progress.state, log: inputs.progress.log, settings: {} }
const queue = buildQueue(saved, now, inputs.newPerDay)

test("the totals' three parts are the deck's cards, so the bar and its labels add up to one count", () => {
  const t = totals(saved, now, queue.length)
  assert.equal(t.cards, inputs.cards.length)
  assert.equal(t.mature + t.learning + t.unseen, t.cards)
})

test("the forecast counts each card once, however many times it comes up, and never more than the deck", () => {
  const f = forecast(saved, now, queue, inputs.newPerDay)
  const showings = f.days.reduce((n, d) => n + d.seen + d.fresh, 0)
  assert.ok(showings > f.cards, `${showings} showings, ${f.cards} cards`)
  assert.equal(f.cards, inputs.cards.length)
})

test("answering a waiting card Good moves it from today's bar to the bar of its new date", () => {
  const id = queue.find((x: string) => saved.state[x])!
  const before = forecast(saved, now, queue, inputs.newPerDay).days
  const next = graded(saved.state[id], 3, now)
  const after = forecast({ ...saved, state: { ...saved.state, [id]: next } }, now, queue.filter((x: string) => x !== id), inputs.newPerDay).days
  const at = next.interval
  assert.equal(after[0].seen, before[0].seen - 1)
  assert.equal(after[at].seen, before[at].seen + 1)
})
