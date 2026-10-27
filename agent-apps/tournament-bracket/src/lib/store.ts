import { cleanPicks, cleanResults, resultsList, type Bracket, type Picks, type Results } from "@/lib/bracket"
import type { AppConfig } from "@/lib/config"

// Everything a person enters is kept under this one key, on this device only.
export const STORAGE_KEY = "tournament-bracket"

export type Saved = { from: string; results: Results; picks: Picks }

export type ExportFile = {
  app: "tournament-bracket"
  title: string
  entrants: string[]
  results: { match: string; winner: string; score?: string }[]
  picks: Picks
}

/** What the inputs file says; when it changes, the hosted page takes its results and picks over the saved ones. */
export function fingerprint(config: AppConfig): string {
  return JSON.stringify([config.entrants, config.results, config.picks])
}

function fromConfig(bracket: Bracket, config: AppConfig): { results: Results; picks: Picks } {
  const results: Results = {}
  for (const r of config.results) results[r.match] = { winner: r.winner, ...(r.score ? { score: r.score } : {}) }
  const picks: Picks = {}
  for (const person of config.people) picks[person] = cleanPicks(bracket, config.picks[person] ?? {})
  return { results: cleanResults(bracket, results), picks }
}

export function load(bracket: Bracket, config: AppConfig): { results: Results; picks: Picks } {
  const base = fromConfig(bracket, config)
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as Saved | null
    if (!saved || saved.from !== fingerprint(config)) return base
    const picks: Picks = {}
    for (const person of config.people) picks[person] = cleanPicks(bracket, saved.picks?.[person] ?? {})
    return { results: cleanResults(bracket, saved.results ?? {}), picks }
  } catch {
    return base
  }
}

export function save(config: AppConfig, results: Results, picks: Picks) {
  const saved: Saved = { from: fingerprint(config), results, picks }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
}

export function toExport(bracket: Bracket, config: AppConfig, results: Results, picks: Picks): ExportFile {
  return { app: "tournament-bracket", title: config.title, entrants: config.entrants, results: resultsList(bracket, results), picks }
}

/** Reads an export back; null when the text is not one. */
export function fromExport(bracket: Bracket, config: AppConfig, text: string): { results: Results; picks: Picks } | null {
  try {
    const file = JSON.parse(text) as Partial<ExportFile>
    if (file.app !== "tournament-bracket" || !Array.isArray(file.results)) return null
    const results: Results = {}
    for (const r of file.results) {
      if (r && typeof r.match === "string" && typeof r.winner === "string") {
        results[r.match] = { winner: r.winner, ...(typeof r.score === "string" && r.score ? { score: r.score } : {}) }
      }
    }
    const picks: Picks = {}
    for (const person of config.people) picks[person] = cleanPicks(bracket, file.picks?.[person] ?? {})
    return { results: cleanResults(bracket, results), picks }
  } catch {
    return null
  }
}

export function download(file: ExportFile) {
  const blob = new Blob([JSON.stringify(file, null, 2) + "\n"], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = "tournament-bracket.json"
  a.click()
  URL.revokeObjectURL(url)
}
