// A company's mark: its initials on a color of its own, the hue taken from its name so it is the same on every visit.
export function initials(company: string): string {
  const words = company.replace(/&/g, " ").split(/\s+/).filter((w) => /[a-z0-9]/i.test(w))
  if (words.length === 0) return "?"
  if (words.length === 1) return words[0].slice(0, 1).toUpperCase()
  return (words[0][0] + words[1][0]).toUpperCase()
}

// The hues a mark is drawn in: around the wheel, leaving out the olive greens and mustards that read as muddy.
const HUES = [18, 32, 48, 62, 145, 160, 175, 192, 210, 228, 248, 266, 284, 302, 322, 345]

export function hue(company: string): number {
  let h = 2166136261
  for (const ch of company) h = Math.imul(h ^ ch.charCodeAt(0), 16777619)
  return HUES[(h >>> 0) % HUES.length]
}

export interface Pay {
  low: string
  high: string | null
  rest: string
}

// "$158k to $182k" becomes { low: "158k", high: "182k" }; anything else is shown as written.
export function readPay(pay: string): Pay | null {
  const m = /^\s*\$\s?([\d.,]+\s?[kKmM]?)\s*(?:(?:to|-|–|—)\s*\$?\s?([\d.,]+\s?[kKmM]?))?\s*(.*)$/.exec(pay)
  if (!m) return null
  return { low: m[1].replace(/\s/g, ""), high: m[2] ? m[2].replace(/\s/g, "") : null, rest: m[3].trim() }
}
