import { buildBracket, seedOrder, type Bracket, type Picks, type Results } from "@/lib/bracket"
import type { AppConfig } from "@/lib/config"
import { fromExport, toExport } from "@/lib/store"

// ?selftest=1 checks the seeding table for every field from 4 to 64, the match nodes on the page, and that an export
// reads back to the same picks and results.

export function selftest(bracket: Bracket, config: AppConfig, results: Results, picks: Picks): string[] {
  const problems: string[] = []
  for (let n = 4; n <= 64; n++) {
    const names = Array.from({ length: n }, (_, i) => `E${i + 1}`)
    const b = buildBracket(names, {})
    if (b.matches.length !== n - 1) problems.push(`${n} entrants: ${b.matches.length} matches, expected ${n - 1}`)
    if (b.byes.length !== b.size - n) problems.push(`${n} entrants: ${b.byes.length} byes, expected ${b.size - n}`)
    const byeSeeds = b.byes.map((e) => e.seed).sort((x, y) => x - y)
    if (byeSeeds.some((s, i) => s !== i + 1)) problems.push(`${n} entrants: byes went to seeds ${byeSeeds.join(", ")}`)
    const order = seedOrder(b.size)
    if (order[0] !== 1 || order[order.length / 2] !== 2) problems.push(`${n} entrants: seeds 1 and 2 share a half`)
  }
  const nodes = document.querySelectorAll("svg [data-match]").length
  if (nodes && nodes !== config.entrants.length - 1) problems.push(`the page shows ${nodes} match nodes, expected ${config.entrants.length - 1}`)
  const text = JSON.stringify(toExport(bracket, config, results, picks))
  const back = fromExport(bracket, config, text)
  if (!back) problems.push("the export did not read back")
  else if (JSON.stringify(sorted(back.results)) !== JSON.stringify(sorted(results)) || JSON.stringify(sorted(back.picks)) !== JSON.stringify(sorted(picks))) {
    problems.push("the export read back different picks or results")
  }
  return problems
}

function sorted(o: object): unknown {
  return Object.fromEntries(
    Object.entries(o)
      .sort(([a], [b]) => (a < b ? -1 : 1))
      .map(([k, v]) => [k, v && typeof v === "object" ? sorted(v) : v]),
  )
}
