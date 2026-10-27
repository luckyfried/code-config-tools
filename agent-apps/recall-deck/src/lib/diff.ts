// A character diff of a typed answer against the right one: the longest common subsequence, then a walk that marks
// each character as kept, missing (in the answer, not typed), or extra (typed, not in the answer).

export type Piece = { kind: "same" | "missing" | "extra"; text: string }

const fold = (s: string) => s.normalize("NFC")

export function charDiff(typed: string, answer: string): Piece[] {
  const a = [...fold(typed)]
  const b = [...fold(answer)]
  const eq = (x: string, y: string) => x.toLocaleLowerCase() === y.toLocaleLowerCase()
  const n = a.length
  const m = b.length
  const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0))
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      lcs[i][j] = eq(a[i], b[j]) ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1])
  const out: Piece[] = []
  const push = (kind: Piece["kind"], ch: string) => {
    const last = out.at(-1)
    if (last && last.kind === kind) last.text += ch
    else out.push({ kind, text: ch })
  }
  let i = 0
  let j = 0
  while (i < n && j < m) {
    if (eq(a[i], b[j])) {
      push("same", b[j])
      i++
      j++
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) push("extra", a[i++])
    else push("missing", b[j++])
  }
  while (i < n) push("extra", a[i++])
  while (j < m) push("missing", b[j++])
  return out
}

export const normalize = (s: string) => fold(s).trim().replace(/\s+/g, " ").toLocaleLowerCase()

export const isRight = (typed: string, answer: string) => normalize(typed) === normalize(answer)

/** A believable slip for the first open's walk-through: one letter dropped from the middle of the answer. */
export function slip(answer: string): string {
  const chars = [...answer]
  const mid = Math.floor(chars.length * 0.6)
  for (let k = 0; k < chars.length; k++) {
    const at = (mid + k) % chars.length
    if (/\p{L}/u.test(chars[at]) && at > 0) return [...chars.slice(0, at), ...chars.slice(at + 1)].join("")
  }
  return answer.slice(0, -1)
}
