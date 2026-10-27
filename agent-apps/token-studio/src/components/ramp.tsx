import { memo, useEffect, useLayoutEffect, useRef } from "react"
import { cn } from "@/lib/utils"
import type { Step } from "@/lib/tokens"

type Props = {
  title: string
  steps: Step[]
  size?: "lg" | "md"
  live?: boolean
  /** The hue this ramp follows: while it moves the chips fan open, and they flip in, in waves, as it turns. */
  turn?: number
  className?: string
}

/** One flip wave: the duration plus the stagger across ten chips, so a new wave never cuts one short. */
const WAVE_MS = 560
/** How long the hue has to rest before the fan closes. */
const REST_MS = 200

/** One ramp, ten named swatches; a dot marks a step whose chroma was pulled in to stay inside sRGB. */
export const Ramp = memo(function Ramp({ title, steps, size = "md", live = false, turn, className }: Props) {
  const ref = useRef<HTMLOListElement>(null)
  const motion = useRef({ hue: turn, last: 0, parity: false, rest: 0 })

  // The chips flip in once as the ramp first appears; later waves follow the hue below.
  useLayoutEffect(() => {
    const el = ref.current
    if (el && motion.current.hue !== undefined) {
      el.dataset.flip = "a"
      motion.current.last = performance.now()
    }
  }, [])

  useLayoutEffect(() => {
    const el = ref.current
    const m = motion.current
    if (!el || turn === undefined || turn === m.hue) return
    m.hue = turn
    const wave = () => {
      m.parity = !m.parity
      el.dataset.flip = m.parity ? "b" : "a"
      m.last = performance.now()
    }
    el.dataset.fan = ""
    if (performance.now() - m.last >= WAVE_MS) wave()
    clearTimeout(m.rest)
    m.rest = window.setTimeout(() => delete el.dataset.fan, REST_MS)
  }, [turn])

  useEffect(() => {
    const m = motion.current
    return () => clearTimeout(m.rest)
  }, [])

  return (
    <figure className={cn("flex flex-col gap-2", className)}>
      <figcaption className="ramp-caption section-label">
        {title}
        <span className="ramp-caption-note">{steps.some((s) => s.clamped) ? "• pulled into sRGB" : "all in sRGB"}</span>
      </figcaption>
      <ol ref={ref} className="ramp" data-size={size} data-turn={turn === undefined ? undefined : ""} data-live={live ? steps[0].name.split("-")[0] : undefined}>
        {steps.map((s) => (
          <li key={s.name} className="swatch" data-swatch={s.name} data-ink={s.l > 0.6 ? "dark" : "light"}>
            <span className="swatch-step tabular-nums">{s.step}</span>
            <span className="swatch-hex font-mono tabular-nums">{s.hex.slice(1)}</span>
            {s.clamped ? <span className="swatch-dot" aria-label="pulled into sRGB" /> : null}
          </li>
        ))}
      </ol>
    </figure>
  )
})
