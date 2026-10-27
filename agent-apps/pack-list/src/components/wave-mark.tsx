import { useId } from "react"
import { cn } from "@/lib/utils"

/** One sine layer 60 units wide with a 12-unit period, closed below, so it can slide two periods across the box. */
function ripple(amplitude: number) {
  let d = `M0 0Q3 ${-amplitude * 2} 6 0`
  for (let x = 12; x <= 60; x += 6) d += `T${x} 0`
  return `${d}V40H0Z`
}
const FRONT = ripple(1.7)
const BACK = ripple(2.3)

type WaveMarkProps = { on: boolean; round?: boolean; className?: string }

/** The bag's fill in small: an ink-outlined pocket the wave climbs into when on, with the check drawn over it. */
export function WaveMark({ on, round, className }: WaveMarkProps) {
  const clip = useId()
  const shape = round ? <circle cx="12" cy="12" r="10.75" /> : <rect x="1.25" y="1.25" width="21.5" height="21.5" rx="6.5" />
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      data-on={on || undefined}
      className={cn("wave-mark block size-6 shrink-0 overflow-visible", className)}
    >
      <defs>
        <clipPath id={clip}>{shape}</clipPath>
      </defs>
      <g className="fill-bag-empty">{shape}</g>
      <g clipPath={`url(#${clip})`}>
        <g className="wave-mark-level">
          <path d={BACK} className="wave-mark-back fill-bag-back" />
          <path d={FRONT} className="wave-mark-front fill-bag" />
        </g>
      </g>
      <g className="fill-none stroke-bag-line" strokeWidth="1.75">
        {shape}
      </g>
      <path
        d="M7 12.4 10.5 15.7 17.2 8.6"
        pathLength={1}
        className="check-path fill-none stroke-bag-empty"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
