import type { CSSProperties } from "react"

// A ring that draws itself to the recipe's minutes (a full ring is an hour; a second, inner ring counts past it),
// and the servings as tiny plates.
export function TimeRing({ minutes, size = 26 }: { minutes: number; size?: number }) {
  const outer = 10
  const inner = 5.5
  const c1 = 2 * Math.PI * outer
  const c2 = 2 * Math.PI * inner
  const first = Math.min(minutes, 60) / 60
  const second = Math.min(Math.max(minutes - 60, 0), 60) / 60
  const arc = (c: number, frac: number) => ({ "--from": `${c}`, "--to": `${c * (1 - frac)}`, strokeDasharray: c }) as CSSProperties
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" className="shrink-0 -rotate-90" aria-hidden>
      <circle cx="13" cy="13" r={outer} fill="none" stroke="var(--ring-track)" strokeWidth="3" />
      <circle className="ring-arc" cx="13" cy="13" r={outer} fill="none" stroke="var(--ring-arc)" strokeWidth="3"
        strokeLinecap="round" style={arc(c1, first)} />
      {second > 0 && (
        <circle className="ring-arc" cx="13" cy="13" r={inner} fill="none" stroke="var(--ring-arc)" strokeWidth="2.4"
          strokeLinecap="round" opacity="0.7" style={arc(c2, second)} />
      )}
    </svg>
  )
}

export function Plates({ servings }: { servings: number }) {
  const shown = Math.min(servings, 6)
  return (
    <span className="inline-flex items-center gap-[3px]" title={`Serves ${servings}`}>
      <span className="sr-only">Serves {servings}</span>
      {Array.from({ length: shown }, (_, n) => (
        <svg key={n} width="11" height="11" viewBox="0 0 12 12" aria-hidden>
          <circle cx="6" cy="6" r="5.4" fill="var(--plate)" opacity="0.35" />
          <circle cx="6" cy="6" r="5.4" fill="none" stroke="var(--plate)" strokeWidth="1.1" />
          <circle cx="6" cy="6" r="3" fill="none" stroke="var(--plate)" strokeWidth="0.9" />
        </svg>
      ))}
      {servings > shown && <span className="text-[11px]">+{servings - shown}</span>}
    </span>
  )
}
