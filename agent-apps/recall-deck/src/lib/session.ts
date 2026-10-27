// Today's queue, the thirty-day forecast, and the totals, all derived from the deck and the saved progress.

import { config, type Card, type CardState } from "./config.ts"
import { addDays, daysBetween } from "./dates.ts"
import { FRESH, QUALITY, answered, byGrade, type Grade } from "./sm2.ts"
import type { Saved } from "./store.ts"

export const FORECAST_DAYS = 30

/** Cards due today (oldest first), then today's unseen cards up to the day's allowance. */
export function buildQueue(saved: Saved, now: string, newPerDay: number, extra = 0): string[] {
  const due: Card[] = []
  const unseen: Card[] = []
  for (const c of config.cards) {
    const s = saved.state[c.id]
    if (!s) unseen.push(c)
    else if (s.due <= now) due.push(c)
  }
  due.sort((a, b) => (saved.state[a.id].due < saved.state[b.id].due ? -1 : saved.state[a.id].due > saved.state[b.id].due ? 1 : 0))
  const allowance = Math.max(0, newPerDay + extra - (saved.log[now]?.fresh ?? 0))
  return [...due, ...unseen.slice(0, allowance)].map((c) => c.id)
}

/** The schedule a grade would give this card today. */
export function graded(state: CardState | undefined, grade: Grade, now: string): CardState {
  const s = byGrade(state ?? { ...FRESH, due: now }, grade)
  return { ...s, due: addDays(now, s.interval) }
}

export interface ForecastDay {
  day: string
  seen: number
  fresh: number
}

export interface Forecast {
  days: ForecastDay[]
  /** How many of the deck's cards come up at least once in the thirty days; a card that comes up twice counts once. */
  cards: number
}

/**
 * How many cards come up each of the next thirty days if every one is answered Good when it comes up: the cards
 * already scheduled, the ones still waiting in today's queue, and the unseen cards arriving at the day's allowance.
 * A card waiting today counts today only, since its next date is the answer's to set; answering it moves it from
 * today's bar to the bar of its new date.
 */
export function forecast(saved: Saved, now: string, queue: string[], newPerDay: number): Forecast {
  const days: ForecastDay[] = Array.from({ length: FORECAST_DAYS }, (_, i) => ({ day: addDays(now, i), seen: 0, fresh: 0 }))
  const waiting = new Set(queue)
  const follow = (s: { ease: number; interval: number; reps: number }, at: number) => {
    let cur = s
    let t = at
    let added = 0
    while (t < FORECAST_DAYS) {
      cur = answered(cur, QUALITY[3])
      t += cur.interval
      if (t < FORECAST_DAYS) {
        days[t].seen++
        added++
      }
    }
    return added
  }
  let unseenIndex = 0
  let cards = 0
  for (const c of config.cards) {
    const s = saved.state[c.id]
    if (!s) continue
    const at = Math.max(0, daysBetween(now, s.due))
    if (at === 0 && !waiting.has(c.id)) {
      if (follow(s, 0)) cards++
      continue
    }
    if (at < FORECAST_DAYS) {
      days[at].seen++
      if (at > 0) follow(s, at)
      cards++
    }
  }
  const unseen = config.cards.filter((c) => !saved.state[c.id])
  const todayNew = unseen.filter((c) => waiting.has(c.id)).length
  for (let k = 0; k < todayNew; k++) {
    cards++
    days[0].fresh++
  }
  const later = unseen.filter((c) => !waiting.has(c.id))
  for (let d = 1; d < FORECAST_DAYS && unseenIndex < later.length; d++) {
    for (let k = 0; k < newPerDay && unseenIndex < later.length; k++, unseenIndex++) {
      cards++
      days[d].fresh++
      follow(FRESH, d)
    }
  }
  return { days, cards }
}

export interface Totals {
  cards: number
  unseen: number
  learning: number
  mature: number
  dueToday: number
  answers30: number
  recall: number | null
  streak: number
}

export function totals(saved: Saved, now: string, queueLength: number): Totals {
  let unseen = 0
  let learning = 0
  let mature = 0
  for (const c of config.cards) {
    const s = saved.state[c.id]
    if (!s) unseen++
    else if (s.interval >= 21) mature++
    else learning++
  }
  let answers30 = 0
  let again30 = 0
  for (let i = 0; i < 30; i++) {
    const l = saved.log[addDays(now, -i)]
    if (l) {
      answers30 += l.seen
      again30 += l.again
    }
  }
  let streak = 0
  for (let i = saved.log[now]?.seen ? 0 : 1; saved.log[addDays(now, -i)]?.seen; i++) streak++
  return {
    cards: config.cards.length,
    unseen,
    learning,
    mature,
    dueToday: queueLength,
    answers30,
    recall: answers30 ? Math.round((1 - again30 / answers30) * 100) : null,
    streak,
  }
}
