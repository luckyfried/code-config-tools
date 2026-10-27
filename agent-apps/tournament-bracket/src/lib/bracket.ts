// Single elimination with seeds and byes. The field is padded to the next power of two; the missing seeds are the
// top seeds' first opponents, so every bye lands on a top seed and every first-round pair holds at least one entrant.

export type Entrant = { name: string; seed: number; color: string }

export type SlotSource = { kind: "entrant"; entrant: Entrant } | { kind: "match"; id: string }

export type Match = {
  id: string
  round: number
  index: number
  pos: number
  side: "left" | "right" | "center"
  slots: [SlotSource, SlotSource]
  next: { id: string; slot: 0 | 1 } | null
  points: number
}

export type Bracket = {
  size: number
  rounds: number
  entrants: Entrant[]
  byes: Entrant[]
  matches: Match[]
  byId: Map<string, Match>
  byRound: Match[][]
}

export type Result = { winner: string; score?: string }
export type Results = Record<string, Result>
export type Picks = Record<string, Record<string, string>>

export type Played = {
  match: Match
  players: [Entrant | null, Entrant | null]
  winner: Entrant | null
  loser: Entrant | null
  score?: string
  upset: boolean
}

/** Bracket positions for a field of `size`: seed order down the sheet, so 1 and 2 can only meet in the final. */
export function seedOrder(size: number): number[] {
  let order = [1]
  while (order.length < size) {
    const n = order.length * 2
    order = order.flatMap((s) => [s, n + 1 - s])
  }
  return order
}

export function roundName(round: number, rounds: number): string {
  const left = rounds - round
  if (left === 0) return "Final"
  if (left === 1) return "Semifinals"
  if (left === 2) return "Quarterfinals"
  return `Round of ${2 ** (left + 1)}`
}

export function shortRoundName(round: number, rounds: number): string {
  const left = rounds - round
  if (left === 0) return "Final"
  if (left === 1) return "Semis"
  if (left === 2) return "Quarters"
  return `Last ${2 ** (left + 1)}`
}

export function buildBracket(names: string[], colors: Record<string, string>): Bracket {
  const entrants = names.map((name, i) => ({ name, seed: i + 1, color: colors[name] ?? "#888888" }))
  const n = entrants.length
  let size = 2
  while (size < n) size *= 2
  const rounds = Math.log2(size)
  const order = seedOrder(size)

  // A source per position of the current round: a real match feeding it, or an entrant placed there directly.
  let sources: SlotSource[] = []
  const byes: Entrant[] = []
  for (let k = 0; k < size / 2; k++) {
    const a = entrants[order[2 * k] - 1]
    const b = entrants[order[2 * k + 1] - 1]
    if (a && b) sources.push({ kind: "match", id: `pending:${k}` })
    else {
      const through = (a ?? b)!
      byes.push(through)
      sources.push({ kind: "entrant", entrant: through })
    }
  }

  const matches: Match[] = []
  const byRound: Match[][] = []
  // Round one: real pairs only, numbered top to bottom.
  const first: Match[] = []
  sources = sources.map((src, k) => {
    if (src.kind === "entrant") return src
    const a = entrants[order[2 * k] - 1]
    const b = entrants[order[2 * k + 1] - 1]
    const m: Match = {
      id: `R1-${first.length + 1}`,
      round: 1,
      index: first.length,
      pos: k,
      side: rounds === 1 ? "center" : k < size / 4 ? "left" : "right",
      slots: [{ kind: "entrant", entrant: a }, { kind: "entrant", entrant: b }],
      next: null,
      points: 1,
    }
    first.push(m)
    return { kind: "match", id: m.id }
  })
  matches.push(...first)
  byRound.push(first)

  for (let r = 2; r <= rounds; r++) {
    const count = size / 2 ** r
    const round: Match[] = []
    const nextSources: SlotSource[] = []
    for (let k = 0; k < count; k++) {
      const m: Match = {
        id: `R${r}-${k + 1}`,
        round: r,
        index: k,
        pos: k,
        side: r === rounds ? "center" : k < count / 2 ? "left" : "right",
        slots: [sources[2 * k], sources[2 * k + 1]],
        next: null,
        points: 2 ** (r - 1),
      }
      round.push(m)
      nextSources.push({ kind: "match", id: m.id })
    }
    matches.push(...round)
    byRound.push(round)
    sources = nextSources
  }

  const byId = new Map(matches.map((m) => [m.id, m]))
  for (const m of matches) {
    m.slots.forEach((s, slot) => {
      if (s.kind === "match") byId.get(s.id)!.next = { id: m.id, slot: slot as 0 | 1 }
    })
  }
  return { size, rounds, entrants, byes, matches, byId, byRound }
}

/** Plays the results through the bracket in order; a result naming someone who is not in that match is ignored. */
export function play(bracket: Bracket, results: Results): Map<string, Played> {
  const played = new Map<string, Played>()
  const byName = new Map(bracket.entrants.map((e) => [e.name, e]))
  for (const m of bracket.matches) {
    const players = m.slots.map((s) =>
      s.kind === "entrant" ? s.entrant : (played.get(s.id)?.winner ?? null),
    ) as [Entrant | null, Entrant | null]
    const r = results[m.id]
    let winner: Entrant | null = null
    if (r && players[0] && players[1] && (r.winner === players[0].name || r.winner === players[1].name)) {
      winner = byName.get(r.winner)!
    }
    const loser = winner ? (players[0]!.name === winner.name ? players[1] : players[0]) : null
    played.set(m.id, {
      match: m,
      players,
      winner,
      loser,
      score: winner ? r?.score : undefined,
      upset: !!(winner && loser && winner.seed > loser.seed),
    })
  }
  return played
}

/** Drops every result that no longer fits, such as a later result whose winner lost an earlier match that changed. */
export function cleanResults(bracket: Bracket, results: Results): Results {
  const played = play(bracket, results)
  const out: Results = {}
  for (const [id, p] of played) if (p.winner) out[id] = { winner: p.winner.name, ...(p.score ? { score: p.score } : {}) }
  return out
}

/** The two entrants a person expects in each match, from their own earlier picks. */
export function projected(bracket: Bracket, mine: Record<string, string>): Map<string, [Entrant | null, Entrant | null]> {
  const byName = new Map(bracket.entrants.map((e) => [e.name, e]))
  const pickOf = new Map<string, Entrant | null>()
  const out = new Map<string, [Entrant | null, Entrant | null]>()
  for (const m of bracket.matches) {
    const players = m.slots.map((s) => (s.kind === "entrant" ? s.entrant : (pickOf.get(s.id) ?? null))) as [
      Entrant | null,
      Entrant | null,
    ]
    out.set(m.id, players)
    const name = mine[m.id]
    const pick = name && players.some((p) => p?.name === name) ? byName.get(name)! : null
    pickOf.set(m.id, pick)
  }
  return out
}

/** Keeps only picks that follow from the person's own earlier picks. */
export function cleanPicks(bracket: Bracket, mine: Record<string, string>): Record<string, string> {
  const proj = projected(bracket, mine)
  const out: Record<string, string> = {}
  for (const m of bracket.matches) {
    const name = mine[m.id]
    if (name && proj.get(m.id)!.some((p) => p?.name === name)) out[m.id] = name
  }
  return out
}

export type Standing = {
  person: string
  points: number
  correct: number
  decided: number
  possible: number
  champion: Entrant | null
}

export function standings(bracket: Bracket, played: Map<string, Played>, people: string[], picks: Picks): Standing[] {
  const finalId = bracket.byRound[bracket.rounds - 1][0].id
  const byName = new Map(bracket.entrants.map((e) => [e.name, e]))
  const out = people.map((person, order) => {
    const mine = picks[person] ?? {}
    let points = 0
    let correct = 0
    let decided = 0
    let possible = 0
    for (const m of bracket.matches) {
      const p = played.get(m.id)!
      const pick = mine[m.id]
      if (p.winner) {
        decided++
        if (pick === p.winner.name) {
          points += m.points
          correct++
        }
      } else if (pick && !isOut(bracket, played, pick)) possible += m.points
    }
    return {
      person,
      points,
      correct,
      decided,
      possible: points + possible,
      champion: byName.get(mine[finalId] ?? "") ?? null,
      order,
    }
  })
  out.sort((a, b) => b.points - a.points || b.possible - a.possible || a.order - b.order)
  return out.map(({ order: _order, ...s }) => s)
}

function isOut(bracket: Bracket, played: Map<string, Played>, name: string): boolean {
  for (const m of bracket.matches) if (played.get(m.id)!.loser?.name === name) return true
  return false
}

export function resultsList(bracket: Bracket, results: Results) {
  return bracket.matches
    .filter((m) => results[m.id])
    .map((m) => ({ match: m.id, winner: results[m.id].winner, ...(results[m.id].score ? { score: results[m.id].score } : {}) }))
}
