import { useLayoutEffect, useRef, useState } from "react"
import { format, parseISO } from "date-fns"
import type { Units } from "@/lib/config"
import { dayKey, e1rm, fmtE1rm, type LiftSet } from "@/lib/lift"

const MAX_DAYS = 16
/** Below five sessions the points stand alone with the record line; a curve through two points reads as a trend it is not. */
const CURVE_FROM = 5

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(0)
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    setWidth(el.clientWidth)
    const ro = new ResizeObserver(([entry]) => setWidth(Math.round(entry.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, width] as const
}

function niceStep(range: number, count: number) {
  const raw = range / count
  const mag = 10 ** Math.floor(Math.log10(raw))
  const f = raw / mag
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * mag
}

/** A monotone cubic through the points (Fritsch and Carlson), so the curve never overshoots a session. */
function monotonePath(pts: { x: number; y: number }[]) {
  const n = pts.length
  if (n < 2) return ""
  const dx = pts.slice(1).map((p, i) => p.x - pts[i].x)
  const m = pts.slice(1).map((p, i) => (p.y - pts[i].y) / (dx[i] || 1))
  const t = pts.map((_, i) => (i === 0 ? m[0] : i === n - 1 ? m[n - 2] : m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2))
  for (let i = 0; i < n - 1; i++) {
    if (m[i] === 0) {
      t[i] = 0
      t[i + 1] = 0
      continue
    }
    const a = t[i] / m[i]
    const b = t[i + 1] / m[i]
    const s = a * a + b * b
    if (s > 9) {
      const k = 3 / Math.sqrt(s)
      t[i] = k * a * m[i]
      t[i + 1] = k * b * m[i]
    }
  }
  let d = `M${pts[0].x.toFixed(1)} ${pts[0].y.toFixed(1)}`
  for (let i = 0; i < n - 1; i++) {
    const h = dx[i] / 3
    d += `C${(pts[i].x + h).toFixed(1)} ${(pts[i].y + t[i] * h).toFixed(1)} ${(pts[i + 1].x - h).toFixed(1)} ${(pts[i + 1].y - t[i + 1] * h).toFixed(1)} ${pts[i + 1].x.toFixed(1)} ${pts[i + 1].y.toFixed(1)}`
  }
  return d
}

type Props = { sets: LiftSet[]; label: string; units: Units; height?: number }

type Session = { key: string; top: LiftSet; best: number; low: number; count: number }

/** One point per session at its best set, on the line; a glowing gold dot where a session set a record; the session's other sets a faint band below. */
export function E1rmChart({ sets, label, units, height = 240 }: Props) {
  const [ref, width] = useWidth<HTMLDivElement>()
  const allBest = sets.reduce((m, s) => Math.max(m, e1rm(s.weight, s.reps)), 0)

  const days: Session[] = []
  for (const s of sets) {
    const k = dayKey(s.date)
    const v = e1rm(s.weight, s.reps)
    const day = days.at(-1)
    if (day?.key === k) {
      if (v > day.best) {
        day.best = v
        day.top = s
      }
      day.low = Math.min(day.low, v)
      day.count++
    } else days.push({ key: k, top: s, best: v, low: v, count: 1 })
  }
  // A record is a session whose best beats every session before it; the first session sets the mark.
  let before = -1
  const records = new Set<string>()
  days.forEach((d, i) => {
    if (i > 0 && d.best > before + 1e-9) records.add(d.key)
    before = Math.max(before, d.best)
  })
  const shown = days.slice(-MAX_DAYS)

  const pad = { top: 28, right: 16, bottom: 28, left: 44 }
  const innerW = Math.max(0, width - pad.left - pad.right)
  const innerH = height - pad.top - pad.bottom

  // The scale follows the session bests, so the climb fills the chart; the band may run off the bottom.
  const bests = shown.map((d) => d.best)
  let lo = Math.min(...bests, allBest)
  let hi = Math.max(...bests, allBest)
  if (hi - lo < 4) {
    lo -= 4
    hi += 2
  }
  const span = hi - lo
  lo = Math.max(lo - span * 0.6, Math.min(...shown.map((d) => d.low)))
  const step = niceStep((hi - lo) * 1.1, 3)
  lo = Math.max(0, Math.floor(lo / step) * step)
  hi = Math.ceil((hi + span * 0.06) / step) * step
  const y = (v: number) => pad.top + innerH - ((v - lo) / (hi - lo || 1)) * innerH
  const ticks: number[] = []
  for (let v = lo; v <= hi + 1e-9; v += step) ticks.push(v)

  const colW = shown.length ? innerW / shown.length : innerW
  const x = (i: number) => pad.left + colW * (i + 0.5)
  const newestKey = shown.at(-1)?.key
  const points = shown.map((d, i) => ({ d, x: x(i), y: y(d.best), record: records.has(d.key), newest: d.key === newestKey }))
  const curve = shown.length >= CURVE_FROM ? monotonePath(points) : ""
  const floor = shown.map((d, i) => ({ x: x(i), y: Math.min(y(d.low), pad.top + innerH) }))
  const band =
    curve && shown.some((d) => d.count > 1) ? `${curve}${monotonePath([...floor].reverse()).replace(/^M/, "L")}Z` : ""
  const labelDays = shown.length <= 3 ? shown.map((_, i) => i) : [0, Math.floor((shown.length - 1) / 2), shown.length - 1]
  const lastDelay = curve ? 1060 : 300 + points.length * 45
  const fmtDay = (d: Session) => format(parseISO(d.top.date), "MMM d")

  return (
    <div ref={ref} className="relative w-full">
      {width > 0 && sets.length > 0 && allBest > 0 ? (
        <svg
          width={width}
          height={height}
          role="img"
          aria-label={`Estimated one-rep max for ${label}, ${shown.length} ${shown.length === 1 ? "session" : "sessions"}, best ${fmtE1rm(allBest)} ${units}`}
          className="block overflow-visible"
        >
          {ticks.map((v) => (
            <g key={v}>
              <line className="chart-grid" x1={pad.left} x2={width - pad.right} y1={y(v)} y2={y(v)} strokeWidth="1" />
              <text x={pad.left - 8} y={y(v) + 4} textAnchor="end" className="figures fill-muted-foreground text-xs">
                {fmtE1rm(v)}
              </text>
            </g>
          ))}
          <line className="chart-best" x1={pad.left} x2={width - pad.right} y1={y(allBest)} y2={y(allBest)} strokeWidth="1.5" />
          <text x={pad.left + 4} y={y(allBest) - 6} textAnchor="start" className="figures fill-foreground text-xs font-semibold">
            Best {fmtE1rm(allBest)} {units}
          </text>
          {band ? <path className="chart-band" d={band} /> : null}
          {curve ? <path className="chart-line" d={curve} pathLength={1} fill="none" strokeWidth="2.5" strokeLinecap="round" /> : null}
          {points.map((p, i) => (
            <g
              key={p.d.key}
              className="chart-dot"
              data-newest={p.newest ? "" : undefined}
              style={{ "--i": i, "--last-delay": `${lastDelay}ms` } as React.CSSProperties}
            >
              {p.record ? <circle className="chart-halo" cx={p.x} cy={p.y} r="10" /> : null}
              <circle
                data-point=""
                data-record={p.record ? "" : undefined}
                className="chart-point"
                cx={p.x}
                cy={p.y}
                r={p.record ? 5 : 3.5}
              >
                <title>{`${fmtDay(p.d)}: best ${p.d.top.weight} ${units} × ${p.d.top.reps}, e1RM ${fmtE1rm(p.d.best)}${p.record ? ", a record" : ""}. ${p.d.count} ${p.d.count === 1 ? "set" : "sets"}.`}</title>
              </circle>
            </g>
          ))}
          {labelDays.map((i) => (
            <text
              key={shown[i].key}
              x={pad.left + colW * (i + 0.5)}
              y={height - 8}
              textAnchor={shown.length > 3 && i === 0 ? "start" : shown.length > 3 && i === shown.length - 1 ? "end" : "middle"}
              className="fill-muted-foreground text-xs"
            >
              {fmtDay(shown[i])}
            </text>
          ))}
        </svg>
      ) : (
        <div
          className="flex h-(--chart-h) items-center justify-center px-6 text-center text-sm text-muted-foreground text-pretty"
          style={{ "--chart-h": `${height}px` } as React.CSSProperties}
        >
          {sets.length === 0
            ? `No sets of ${label} yet. Log one and its curve starts here.`
            : allBest === 0
              ? `No added weight yet, so there is no max to estimate. Most reps in a set: ${Math.max(...sets.map((s) => s.reps))}.`
              : null}
        </div>
      )}
    </div>
  )
}
