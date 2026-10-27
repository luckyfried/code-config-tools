import { useEffect, useId, useRef, useState } from "react"
import { reducedMotion } from "@/lib/motion"
import type { Deal, Stage } from "@/lib/pipeline"
import { cn } from "@/lib/utils"

const W = 1000
const GAP = 7
const FLOOR = 0.24
const LIP = 16

/** The funnel lying on its side: one smooth body, a segment per stage as tall as its count of deals, colored along the stages' ramp. The body morphs whenever a count changes. */
export function Funnel({ deals, stages, onPick, compact }: { deals: Deal[]; stages: Stage[]; onPick?: (id: string) => void; compact?: boolean }) {
  const counts = stages.map((stage) => deals.filter((deal) => deal.stage === stage.id).length)
  const max = Math.max(1, ...counts)
  const heights = useMorph(counts.map((count) => FLOOR + ((1 - FLOOR) * count) / max))
  const id = useId().replace(/:/g, "")
  const n = stages.length
  const w = W / n

  return (
    <div className="flex flex-col gap-2" data-funnel="">
      <div className={cn("relative", compact ? "h-[84px]" : "h-[118px]")}>
        <svg viewBox={`0 0 ${W} 100`} preserveAspectRatio="none" className="funnel-body absolute inset-0 size-full overflow-visible" aria-hidden="true">
          <defs>
            <linearGradient id={`${id}-ramp`} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={W} y2="0">
              {stages.map((stage, i) => (
                <stop key={stage.id} offset={(i + 0.5) / n} data-stage="" style={{ "--stage-raw": stage.color, stopColor: "var(--stage)" } as React.CSSProperties} />
              ))}
            </linearGradient>
            <linearGradient id={`${id}-sheen`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="white" stopOpacity="0.42" />
              <stop offset="0.38" stopColor="white" stopOpacity="0.06" />
              <stop offset="0.62" stopColor="black" stopOpacity="0" />
              <stop offset="1" stopColor="black" stopOpacity="0.22" />
            </linearGradient>
          </defs>
          {stages.map((stage, i) => {
            const d = segmentPath(heights, i, w)
            return (
              <g key={stage.id}>
                <path d={d} fill={`url(#${id}-ramp)`} />
                <path d={d} fill={`url(#${id}-sheen)`} />
              </g>
            )
          })}
          {/* The spout's rounded end, and the wide mouth seen from the side: its rim lit, its inside in shadow. */}
          <ellipse cx={W - LIP} cy="50" rx={LIP} ry={48 * heights[n - 1]} fill={`url(#${id}-ramp)`} />
          <ellipse cx={W - LIP} cy="50" rx={LIP} ry={48 * heights[n - 1]} fill={`url(#${id}-sheen)`} />
          <ellipse cx={LIP} cy="50" rx={LIP} ry={48 * heights[0]} fill={`url(#${id}-ramp)`} />
          <ellipse cx={LIP} cy="50" rx={LIP * 0.72} ry={48 * heights[0] - 3} className="funnel-mouth" />
        </svg>
        <div className="absolute inset-0 grid" style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}>
          {stages.map((stage, i) => (
            <span
              key={stage.id}
              data-stage=""
              style={{ "--stage-raw": stage.color } as React.CSSProperties}
              className={cn("funnel-count grid place-items-center font-semibold tabular-nums tracking-[-0.02em]", compact ? "text-lg" : "text-[22px]")}
            >
              {counts[i]}
            </span>
          ))}
        </div>
      </div>
      <ol aria-label="Deals in each stage" className="grid" style={{ gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))` }}>
        {stages.map((stage, i) => (
          <li key={stage.id} data-funnel-segment={stage.id} className="min-w-0">
            <button
              type="button"
              onClick={() => onPick?.(stage.id)}
              tabIndex={onPick ? 0 : -1}
              aria-label={`${stage.label}, ${counts[i]} ${counts[i] === 1 ? "deal" : "deals"}`}
              className={cn(
                "block w-full truncate px-0.5 text-center text-xs font-medium tracking-[-0.01em] text-muted-foreground",
                onPick ? "min-h-8 hover:text-foreground" : "pointer-events-none",
              )}
            >
              {stage.label}
            </button>
          </li>
        ))}
      </ol>
    </div>
  )
}

const smooth = (t: number) => t * t * (3 - 2 * t)

/** The body's half-height at `x`: level across the middle of each stage, an S-curve between neighbors. */
function halfAt(heights: number[], x: number, w: number) {
  const n = heights.length
  const i = Math.min(n - 1, Math.max(0, Math.floor(x / w)))
  const t = (x - i * w) / w
  const h = heights[i]
  if (t < 0.42 && i > 0) {
    const edge = (heights[i - 1] + h) / 2
    return edge + (h - edge) * smooth(t / 0.42)
  }
  if (t > 0.58 && i < n - 1) {
    const edge = (heights[i + 1] + h) / 2
    return h + (edge - h) * smooth((t - 0.58) / 0.42)
  }
  return h
}

function segmentPath(heights: number[], i: number, w: number) {
  const from = i === 0 ? LIP : i * w + GAP / 2
  const to = i === heights.length - 1 ? W - LIP : (i + 1) * w - GAP / 2
  const top: string[] = []
  const bottom: string[] = []
  for (let x = from; ; x = Math.min(to, x + 8)) {
    const half = 48 * halfAt(heights, x, w)
    top.push(`${x.toFixed(1)} ${(50 - half).toFixed(2)}`)
    bottom.push(`${x.toFixed(1)} ${(50 + half).toFixed(2)}`)
    if (x >= to) break
  }
  return `M${top.join(" L")} L${bottom.reverse().join(" L")} Z`
}

/** Heights that glide to new values over 600 ms instead of jumping. */
function useMorph(target: number[]) {
  const [shown, setShown] = useState(target)
  const current = useRef(target)
  const key = target.map((h) => h.toFixed(4)).join(",")
  useEffect(() => {
    const from = current.current
    const to = key.split(",").map(Number)
    if (from.length !== to.length || reducedMotion()) {
      current.current = to
      setShown(to)
      return
    }
    const start = performance.now()
    let frame = 0
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / 600)
      const e = 1 - Math.pow(1 - t, 3)
      const next = to.map((h, i) => from[i] + (h - from[i]) * e)
      current.current = next
      setShown(next)
      if (t < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [key])
  return shown.length === target.length ? shown : target
}
