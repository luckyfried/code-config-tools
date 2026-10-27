import { useCallback, useMemo } from "react"
import { ContrastMatrix } from "./contrast-matrix"
import { HueWheel } from "./hue-wheel"
import { LabeledSlider } from "./labeled-slider"
import { Ramp } from "./ramp"
import { SurfaceStrips } from "./surface-strips"
import { useHeldOffscreen } from "@/hooks/use-held-offscreen"
import { color, LIMITS, type Settings, type System } from "@/lib/tokens"

type Props = {
  sys: System
  mode: "light" | "dark"
  showRamps: boolean
  onChange: (update: (s: Settings) => Settings) => void
}

const gradient = (stops: string[]) => `linear-gradient(90deg, ${stops.join(", ")})`
/** The tint slider's track: every hue the grays can lean toward, at a chroma strong enough to read. */
const TINT_TRACK = gradient(Array.from({ length: 13 }, (_, i) => color(0.72, 0.09, i * 30).hex))

export function ColorPanel({ sys, mode, showRamps, onChange }: Props) {
  const s = sys.settings
  const brand500 = sys.brand[5]
  const setHue = useCallback((hue: number) => onChange((p) => ({ ...p, brand: { ...p.brand, hue } })), [onChange])
  const setChroma = useCallback((chroma: number) => onChange((p) => ({ ...p, brand: { ...p.brand, chroma } })), [onChange])
  const setTint = useCallback((neutralHue: number) => onChange((p) => ({ ...p, neutralHue })), [onChange])
  const shown = useMemo(() => ({ pairs: sys.pairs[mode], mode, light: sys.light, dark: sys.dark }), [sys.pairs, mode, sys.light, sys.dark])
  const [lowerRef, lower] = useHeldOffscreen(shown)
  const hue = Math.round(s.brand.hue)
  const chromaTrack = useMemo(() => gradient(Array.from({ length: 8 }, (_, i) => color(0.648, LIMITS.chroma[0] + (i / 7) * (LIMITS.chroma[1] - LIMITS.chroma[0]), hue).hex)), [hue])
  return (
    <div className="flex flex-col gap-7">
      <section className="color-head" aria-label="Brand color">
        <HueWheel hue={s.brand.hue} chroma={s.brand.chroma} onChange={setHue} />
        <div className="color-controls flex min-w-0 flex-1 flex-col gap-5">
          <div className="flex flex-col gap-0.5">
            <p className="section-label">brand-500</p>
            <p className="font-mono text-xl font-medium tabular-nums">{brand500.hex}</p>
            <p className="font-mono text-xs text-balance text-muted-foreground tabular-nums">
              oklch({(brand500.l * 100).toFixed(1)}% {brand500.c.toFixed(3)} {Math.round(brand500.h)})
            </p>
          </div>
          <LabeledSlider
            label="Chroma"
            value={s.brand.chroma}
            min={LIMITS.chroma[0]}
            max={LIMITS.chroma[1]}
            step={0.005}
            display={s.brand.chroma.toFixed(3)}
            track={chromaTrack}
            onChange={setChroma}
          />
          <LabeledSlider
            label="Gray tint"
            value={s.neutralHue}
            min={0}
            max={359}
            step={1}
            display={`${Math.round(s.neutralHue)}°`}
            track={TINT_TRACK}
            onChange={setTint}
          />
        </div>
      </section>
      {showRamps ? (
        <div className="offscreen-skip flex flex-col gap-5">
          <Ramp title="Brand" steps={sys.brand} live turn={s.brand.hue} />
          <Ramp title="Neutral" steps={sys.neutral} live />
        </div>
      ) : null}
      <div ref={lowerRef} className="flex flex-col gap-7">
        <ContrastMatrix pairs={lower.pairs} mode={lower.mode} />
        <SurfaceStrips light={lower.light} dark={lower.dark} />
      </div>
    </div>
  )
}
