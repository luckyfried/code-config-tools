// Runs with: npm test
import { test } from "node:test"
import assert from "node:assert/strict"
import { FRESH, EASY_BONUS, nextEase, answered, byGrade, comesBackToday, type Schedule } from "./sm2.ts"

const run = (qs: number[]): Schedule[] => {
  const out: Schedule[] = []
  let s = FRESH
  for (const q of qs) out.push((s = answered(s, q)))
  return out
}

test("the E-Factor formula from the paper", () => {
  assert.equal(nextEase(2.5, 5), 2.6)
  assert.equal(nextEase(2.5, 4), 2.5)
  assert.equal(nextEase(2.5, 3), 2.36)
  assert.equal(nextEase(1.35, 3), 1.3)
})

test("intervals of 1, 6, then I(n-1) times EF rounded up: the published 1, 6, 15 at EF 2.5", () => {
  assert.deepEqual(run([4, 4, 4, 4]).map((s) => s.interval), [1, 6, 15, 38])
  assert.ok(run([4, 4, 4, 4]).every((s) => s.ease === 2.5))
})

test("perfect answers raise the E-Factor 0.1 each time and stretch the intervals", () => {
  const s = run([5, 5, 5, 5])
  assert.deepEqual(s.map((x) => x.ease), [2.6, 2.7, 2.8, 2.9])
  assert.deepEqual(s.map((x) => x.interval), [1, 6, 18, 53])
})

test("a lapse restarts the repetitions and keeps the E-Factor", () => {
  const s = run([5, 5, 5, 1, 4, 4])
  assert.deepEqual(s[3], { ease: 2.8, interval: 1, reps: 0 })
  assert.deepEqual(s.slice(4).map((x) => x.interval), [1, 6])
})

test("the E-Factor never falls below 1.3", () => {
  const s = run([3, 3, 3, 3, 3, 3, 3, 3, 3])
  assert.equal(s.at(-1)!.ease, 1.3)
})

test("Easy reaches further than Good, and Hard no further", () => {
  const base = run([4, 4])[1]
  const [hard, good, easy] = [3, 4, 5].map((q) => answered(base, q).interval)
  assert.ok(hard <= good && good < easy, `${hard} ${good} ${easy}`)
})

test("a 5 lands at least a day past a 4 even when rounding up would tie them", () => {
  const s = { ease: 2.56, interval: 6, reps: 2 }
  assert.equal(answered(s, 4).interval, 16)
  assert.equal(answered(s, 5).interval, 17)
})

test("only Again comes back the same day; Hard, Good, and Easy go to their intervals", () => {
  assert.deepEqual(([1, 2, 3, 4] as const).map(comesBackToday), [true, false, false, false])
})

test("the four buttons give four different intervals, Easy with the bonus well past Good", () => {
  const s = { ease: 2.56, interval: 6, reps: 2 }
  const [again, hard, good, easy] = ([1, 2, 3, 4] as const).map((g) => byGrade(s, g).interval)
  assert.deepEqual([again, hard, good, easy], [1, 8, 16, 23])
  assert.equal(byGrade(s, 4).interval, Math.ceil(answered(s, 5).interval * EASY_BONUS))
})
