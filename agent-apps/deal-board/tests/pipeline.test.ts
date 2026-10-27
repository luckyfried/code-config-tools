// Run with `npm test` (Node 22.6 or later reads the TypeScript as is).
import assert from "node:assert/strict"
import { test } from "node:test"
import { DAY, LOST, WON, fromExport, latestMoves, moveDeal, newDeal, results, rewind, seedBoard, toExport, weightedTotal, type Stage } from "../src/lib/pipeline.ts"

const stages: Stage[] = [
  { id: "lead", label: "Lead", probability: 10, color: "#5c5be2" },
  { id: "qualified", label: "Qualified", probability: 25, color: "#9e47db" },
  { id: "proposal", label: "Proposal", probability: 50, color: "#e73e9a" },
  { id: "negotiation", label: "Negotiation", probability: 70, color: "#f96c4a" },
  { id: "closing", label: "Closing", probability: 90, color: "#f9ad26" },
]
const now = Date.UTC(2026, 9, 26, 15)

test("a deal moved one stage forward changes the weighted total by value times the change in probability", () => {
  const board = seedBoard([{ company: "Acme", value: 10_000, stage: "proposal" }], stages, now)
  const added = newDeal({ company: "Northwind", value: 12_345, stage: "lead", contact: "", nextStep: "", date: "", notes: "" }, now)
  const before = weightedTotal([...board, added], stages)
  const moved = moveDeal(added, "qualified", now + 1000)
  const after = weightedTotal([...board, moved], stages)
  assert.equal(after - before, (12_345 * (25 - 10)) / 100)
  assert.equal(before, 5_000 + 1_234.5)
  assert.deepEqual(moved.log.at(-1), { at: now + 1000, from: "lead", to: "qualified" })
})

test("won and lost deals leave the weighted total", () => {
  const [deal] = seedBoard([{ company: "Acme", value: 40_000, stage: "closing" }], stages, now)
  assert.equal(weightedTotal([deal], stages), 36_000)
  assert.equal(weightedTotal([moveDeal(deal, WON, now)], stages), 0)
  assert.equal(weightedTotal([moveDeal(deal, LOST, now)], stages), 0)
})

test("seeds count their days back from the day the board is filled", () => {
  const [deal] = seedBoard([{ company: "Acme", value: 1, stage: "proposal", daysInStage: 3, openedDaysAgo: 20, date: 2 }], stages, now)
  assert.equal(deal.enteredAt, now - 3 * DAY)
  assert.equal(deal.createdAt, now - 20 * DAY)
  assert.equal(deal.date, "2026-10-28")
  assert.deepEqual(deal.log.map((move) => [move.from, move.to]), [[null, "qualified"], ["qualified", "proposal"]])
})

test("the ninety-day results count wins, losses, the win rate, and the cycle time", () => {
  const board = seedBoard([
    { company: "A", value: 10_000, stage: WON, daysInStage: 2, openedDaysAgo: 32 },
    { company: "B", value: 20_000, stage: WON, daysInStage: 40, openedDaysAgo: 50 },
    { company: "C", value: 5_000, stage: LOST, daysInStage: 9 },
    { company: "D", value: 99_000, stage: WON, daysInStage: 120 },
  ], stages, now)
  const r = results(board, now)
  assert.equal(r.won, 2)
  assert.equal(r.lost, 1)
  assert.equal(r.wonValue, 30_000)
  assert.equal(r.winRate, 2 / 3)
  assert.equal(r.averageCycle, 20)
  assert.equal(r.weeks.length, 13)
  assert.equal(r.weeks.at(-1)?.won, 10_000)
})

test("the board replays its latest day's moves from where they started", () => {
  const board = seedBoard([
    { company: "A", value: 1, stage: "proposal", daysInStage: 0.2 },
    { company: "B", value: 1, stage: WON, daysInStage: 0.1 },
    { company: "C", value: 1, stage: "lead", daysInStage: 0 },
    { company: "D", value: 1, stage: "negotiation", daysInStage: 6 },
  ], stages, now)
  const moves = latestMoves(board)
  assert.deepEqual(moves.map(({ deal }) => deal.company), ["A", "B"])
  const before = rewind(board, moves.map(({ move }) => move), moves.map(({ deal }) => deal.id))
  assert.deepEqual(before.map((deal) => deal.stage), ["qualified", "closing", "lead", "negotiation"])
})

test("an export reads back as the same deals", () => {
  const board = seedBoard([{ company: "Acme", value: 10_000, stage: "proposal", contact: "Dana", nextStep: "Call", date: "2026-11-02", notes: "Likes Tuesdays" }], stages, now)
  const file = JSON.stringify(toExport(board, stages, "USD", now))
  assert.deepEqual(fromExport(file, stages, now), board)
  assert.equal(typeof fromExport("not json", stages, now), "string")
})
