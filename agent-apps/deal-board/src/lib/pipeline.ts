// The board's arithmetic and its data, with no React and no browser in it, so Node tests it as is.

export const DAY = 86_400_000
export const WON = "won"
export const LOST = "lost"
export type Outcome = typeof WON | typeof LOST

export interface Stage {
  id: string
  label: string
  /** The chance a deal in this stage closes, 0 to 100. */
  probability: number
  color: string
}

export interface SeedDeal {
  company: string
  value: number
  stage: string
  contact?: string
  nextStep?: string
  date?: string | number
  notes?: string
  daysInStage?: number
  openedDaysAgo?: number
  from?: string
}

export interface Move {
  at: number
  from: string | null
  to: string
}

export interface Deal {
  id: string
  company: string
  value: number
  /** A stage id, or "won" or "lost". */
  stage: string
  contact: string
  nextStep: string
  /** The next step's date, YYYY-MM-DD, or empty. */
  date: string
  notes: string
  createdAt: number
  enteredAt: number
  log: Move[]
}

export const isClosed = (deal: Deal) => deal.stage === WON || deal.stage === LOST

/** Each open deal's value times its stage's probability, summed. Value and probability are whole numbers, so the sum is exact in hundredths. */
export function weightedTotal(deals: Deal[], stages: Stage[]): number {
  const chance = new Map(stages.map((stage) => [stage.id, stage.probability]))
  let hundredths = 0
  for (const deal of deals) hundredths += deal.value * (chance.get(deal.stage) ?? 0)
  return hundredths / 100
}

export function openTotal(deals: Deal[]): number {
  return deals.reduce((sum, deal) => (isClosed(deal) ? sum : sum + deal.value), 0)
}

export function stageSummary(deals: Deal[], stage: Stage) {
  const inStage = deals.filter((deal) => deal.stage === stage.id)
  const value = inStage.reduce((sum, deal) => sum + deal.value, 0)
  return { count: inStage.length, value, weighted: (value * stage.probability) / 100 }
}

/** The deal after a move to `to` at `at`; the same deal when it is already there. */
export function moveDeal(deal: Deal, to: string, at: number): Deal {
  if (deal.stage === to) return deal
  return { ...deal, stage: to, enteredAt: at, log: [...deal.log, { at, from: deal.stage, to }] }
}

/** Whole days a deal has sat in its stage. */
export const daysInStage = (deal: Deal, now: number) => Math.max(0, Math.floor((now - deal.enteredAt) / DAY))

/** How far a deal has aged, 0 fresh to 1 stale at 30 days; the ring stays neutral for a week, warms to amber at 14 days and to red at 30. */
export const AGE_FRESH_DAYS = 7
export const AGE_WARM_DAYS = 14
export const AGE_STALE_DAYS = 30
export const ageFraction = (days: number) => Math.min(1, days / AGE_STALE_DAYS)
const clamp01 = (n: number) => Math.max(0, Math.min(1, n))
/** The ring's two color steps: neutral to amber over the second week, amber to red by thirty days. */
export const ageWarmth = (days: number) => ({
  toWarm: clamp01((days - AGE_FRESH_DAYS) / (AGE_WARM_DAYS - AGE_FRESH_DAYS)),
  toStale: clamp01((days - AGE_WARM_DAYS) / (AGE_STALE_DAYS - AGE_WARM_DAYS)),
})

/** The stage a closed deal left, read from its log; the first stage when the log does not say. */
export function stageBefore(deal: Deal, stages: Stage[]): string {
  const ids = new Set(stages.map((stage) => stage.id))
  for (let i = deal.log.length - 1; i >= 0; i--) {
    const from = deal.log[i].from
    if (from !== null && ids.has(from)) return from
  }
  return stages[0]?.id ?? ""
}

export function closedAt(deal: Deal): number | null {
  return isClosed(deal) ? deal.enteredAt : null
}

const isoDay = (ms: number) => new Date(ms).toISOString().slice(0, 10)

/** A seed's date: "YYYY-MM-DD" as written, or a number of days from the day the board is first filled. */
export function seedDate(date: string | number | undefined, now: number): string {
  if (typeof date === "number") return isoDay(now + Math.round(date) * DAY)
  return typeof date === "string" && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : ""
}

/** The first board, filled from the inputs' seedDeals. Days given in the seeds count back from `now`. */
export function seedBoard(seeds: SeedDeal[], stages: Stage[], now: number): Deal[] {
  const ids = stages.map((stage) => stage.id)
  return seeds.map((seed, index) => {
    const closed = seed.stage === WON || seed.stage === LOST
    const at = closed ? ids.length : Math.max(0, ids.indexOf(seed.stage))
    const stage = closed ? seed.stage : ids[at] ?? ids[0]
    const days = Math.max(0, seed.daysInStage ?? 0)
    const entered = Math.round(now - days * DAY)
    const from = seed.from !== undefined && ids.includes(seed.from) ? seed.from : at > 0 ? ids[at - 1] : null
    const opened = Math.round(now - Math.max(days, seed.openedDaysAgo ?? days + 5 * at) * DAY)
    const log: Move[] = from === null || opened >= entered
      ? [{ at: entered, from: null, to: stage }]
      : [{ at: opened, from: null, to: from }, { at: entered, from, to: stage }]
    return {
      id: `seed-${index + 1}`,
      company: seed.company,
      value: Math.round(seed.value),
      stage,
      contact: seed.contact ?? "",
      nextStep: seed.nextStep ?? "",
      date: seedDate(seed.date, now),
      notes: seed.notes ?? "",
      createdAt: log[0].at,
      enteredAt: entered,
      log,
    }
  })
}

/** Deals whose stage the inputs no longer name go to the first stage, so none is lost from sight. */
export function fitToStages(deals: Deal[], stages: Stage[]): Deal[] {
  const ids = new Set(stages.map((stage) => stage.id))
  const first = stages[0]?.id
  return deals.map((deal) => (isClosed(deal) || ids.has(deal.stage) || !first ? deal : { ...deal, stage: first }))
}

export interface Week {
  /** Weeks back from now; 0 is the current week. */
  index: number
  won: number
  lost: number
  wonCount: number
  lostCount: number
}

/** Won and lost over the last ninety days, in weeks oldest first, with the win rate and the average cycle time of the wins. */
export function results(deals: Deal[], now: number, days = 90) {
  const count = Math.ceil(days / 7)
  const weeks: Week[] = Array.from({ length: count }, (_, i) => ({ index: count - 1 - i, won: 0, lost: 0, wonCount: 0, lostCount: 0 }))
  const cycles: { deal: Deal; days: number }[] = []
  let won = 0
  let lost = 0
  let wonValue = 0
  let lostValue = 0
  for (const deal of deals) {
    const at = closedAt(deal)
    if (at === null || at < now - days * DAY || at > now) continue
    const week = weeks[weeks.length - 1 - Math.floor((now - at) / (7 * DAY))]
    if (deal.stage === WON) {
      won++
      wonValue += deal.value
      if (week) {
        week.won += deal.value
        week.wonCount++
      }
      cycles.push({ deal, days: Math.max(0, Math.round((at - deal.createdAt) / DAY)) })
    } else {
      lost++
      lostValue += deal.value
      if (week) {
        week.lost += deal.value
        week.lostCount++
      }
    }
  }
  const winRate = won + lost === 0 ? null : won / (won + lost)
  const averageCycle = cycles.length === 0 ? null : cycles.reduce((sum, cycle) => sum + cycle.days, 0) / cycles.length
  cycles.sort((a, b) => a.days - b.days)
  return { weeks, won, lost, wonValue, lostValue, winRate, averageCycle, cycles }
}

/** The moves of the board's latest day, oldest first, at most `limit`: what the board replays when it opens. */
export function latestMoves(deals: Deal[], limit = 3): { deal: Deal; move: Move }[] {
  const moves = deals.flatMap((deal) => deal.log.filter((move) => move.from !== null).map((move) => ({ deal, move })))
  if (moves.length === 0) return []
  moves.sort((a, b) => a.move.at - b.move.at)
  const last = moves[moves.length - 1].move.at
  const sameDay = moves.filter(({ move }) => last - move.at < DAY / 2)
  const latest = new Map<string, { deal: Deal; move: Move }>()
  for (const entry of sameDay) latest.set(entry.deal.id, entry)
  // Only a deal's own last move can be replayed, since the board shows where each deal is now.
  return [...latest.values()].filter(({ deal, move }) => deal.log[deal.log.length - 1] === move).slice(-limit)
}

/** The board as it stood before `moves`: each of those deals back in the stage it moved from. */
export function rewind(deals: Deal[], moves: Move[], dealIds: string[]): Deal[] {
  const back = new Map(dealIds.map((id, i) => [id, moves[i]]))
  return deals.map((deal) => {
    const move = back.get(deal.id)
    return move && move.from !== null ? { ...deal, stage: move.from } : deal
  })
}

export interface Export {
  app: "deal-board"
  exportedAt: string
  currency: string
  stages: Stage[]
  deals: Deal[]
}

export function toExport(deals: Deal[], stages: Stage[], currency: string, now: number): Export {
  return { app: "deal-board", exportedAt: new Date(now).toISOString(), currency, stages, deals }
}

const text = (value: unknown) => (typeof value === "string" ? value : "")
const time = (value: unknown, fallback: number) => (typeof value === "number" && Number.isFinite(value) ? value : fallback)

/** Deals read back from an export (or a bare list of deals); a plain sentence when the file is not one. */
export function fromExport(raw: string, stages: Stage[], now: number): Deal[] | string {
  let data: unknown
  try {
    data = JSON.parse(raw)
  } catch {
    return "That file is not a Deal Board export."
  }
  const list = Array.isArray(data) ? data : (data as { deals?: unknown })?.deals
  if (!Array.isArray(list)) return "That file has no deals in it."
  const ids = new Set([...stages.map((stage) => stage.id), WON, LOST])
  const seen = new Set<string>()
  const deals: Deal[] = []
  for (const [index, item] of list.entries()) {
    const d = item as Record<string, unknown>
    if (typeof d !== "object" || d === null || typeof d.company !== "string" || typeof d.value !== "number") {
      return `Deal ${index + 1} in that file has no company or value.`
    }
    let id = typeof d.id === "string" && d.id !== "" ? d.id : `deal-${index + 1}`
    while (seen.has(id)) id = `${id}-copy`
    seen.add(id)
    const stage = typeof d.stage === "string" && ids.has(d.stage) ? d.stage : stages[0]?.id ?? ""
    const enteredAt = time(d.enteredAt, now)
    const log = Array.isArray(d.log)
      ? d.log.flatMap((m: Record<string, unknown>) => (typeof m?.to === "string" ? [{ at: time(m.at, enteredAt), from: typeof m.from === "string" ? m.from : null, to: m.to }] : []))
      : []
    deals.push({
      id,
      company: d.company,
      value: Math.max(0, Math.round(d.value)),
      stage,
      contact: text(d.contact),
      nextStep: text(d.nextStep),
      date: /^\d{4}-\d{2}-\d{2}$/.test(text(d.date)) ? text(d.date) : "",
      notes: text(d.notes),
      createdAt: time(d.createdAt, log[0]?.at ?? enteredAt),
      enteredAt,
      log: log.length > 0 ? log : [{ at: enteredAt, from: null, to: stage }],
    })
  }
  return deals
}

export function newDeal(fields: Pick<Deal, "company" | "value" | "stage" | "contact" | "nextStep" | "date" | "notes">, now: number): Deal {
  const id = `deal-${now.toString(36)}-${Math.floor(Math.random() * 1e6).toString(36)}`
  return { ...fields, id, createdAt: now, enteredAt: now, log: [{ at: now, from: null, to: fields.stage }] }
}
