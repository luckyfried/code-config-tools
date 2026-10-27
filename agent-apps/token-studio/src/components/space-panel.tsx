import { LIMITS, type Settings, type System } from "@/lib/tokens"
import { LabeledSlider } from "./labeled-slider"

type Props = {
  sys: System
  onChange: (update: (s: Settings) => Settings) => void
}

export function SpacePanel({ sys, onChange }: Props) {
  const s = sys.settings
  return (
    <div className="flex flex-col gap-7">
      <LabeledSlider
        label="Base unit"
        value={s.spacingBase}
        min={LIMITS.spacingBase[0]}
        max={LIMITS.spacingBase[1]}
        step={1}
        display={`${s.spacingBase} px`}
        onChange={(spacingBase) => onChange((p) => ({ ...p, spacingBase }))}
      />
      <figure className="flex flex-col gap-3">
        <figcaption className="section-label">The steps</figcaption>
        <ol className="space-bars" data-live="space">
          {sys.space.map((sp, i) => (
            <li key={sp.name} className="space-bar" data-space={i + 1}>
              <span className="font-mono text-xs text-muted-foreground">{sp.name}</span>
              <span className="space-track">
                <span className="space-fill" />
              </span>
              <span className="text-right font-mono text-xs tabular-nums">{sp.px}px</span>
            </li>
          ))}
        </ol>
      </figure>
      <figure className="flex flex-col gap-3">
        <figcaption className="section-label">In use</figcaption>
        <div className="space-demo gen light" data-live="">
          <div className="space-demo-card">
            <span className="space-demo-chip" />
            <span className="space-demo-line" />
            <span className="space-demo-line space-demo-line-short" />
            <span className="space-demo-row">
              <span className="space-demo-button" />
              <span className="space-demo-button space-demo-button-quiet" />
            </span>
          </div>
        </div>
        <p className="text-xs text-muted-foreground">Card padding is space-5, the gaps space-2 and space-3.</p>
      </figure>
    </div>
  )
}
