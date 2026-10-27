import { memo, useId, useLayoutEffect, useRef } from "react"
import { Slider } from "@/components/ui/slider"

type Props = {
  label: string
  value: number
  min: number
  max: number
  step: number
  display: string
  /** A CSS gradient painted on the track, showing what the slider's range does to the color. */
  track?: string
  onChange: (value: number) => void
}

export const LabeledSlider = memo(function LabeledSlider({ label, value, min, max, step, display, track, onChange }: Props) {
  const id = useId()
  const ref = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    if (track) ref.current?.style.setProperty("--track", track)
  }, [track])
  return (
    <div ref={ref} className="flex flex-col gap-2.5" data-track={track ? "" : undefined}>
      <div className="flex items-baseline justify-between gap-3 text-sm">
        <span id={id} className="font-medium whitespace-nowrap">
          {label}
        </span>
        <span className="slider-value font-mono tabular-nums">{display}</span>
      </div>
      <Slider
        aria-labelledby={id}
        className="studio-slider"
        min={min}
        max={max}
        step={step}
        value={[value]}
        onValueChange={(next) => onChange(Array.isArray(next) ? next[0] : next)}
      />
    </div>
  )
})
