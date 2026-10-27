import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { formatHeight, formatPace, heightUnit, paceLabel, usesSpeed } from "@/lib/format"
import { metricValues, spread } from "@/lib/track"
import type { ColorBy, Track, Units } from "@/lib/types"

interface ColorKeyProps {
  track: Track
  units: Units
  colorBy: ColorBy
  onChange: (next: ColorBy) => void
}

function ends(track: Track, colorBy: ColorBy, units: Units): [string, string] {
  const values = metricValues(track, colorBy) ?? track.v
  const [lo, hi] = spread(values)
  if (colorBy === "heart") return [`${Math.round(lo)} bpm`, `${Math.round(hi)} bpm`]
  if (colorBy === "elevation") return [`${formatHeight(lo, units)} ${heightUnit(units)}`, `${formatHeight(hi, units)} ${heightUnit(units)}`]
  const unit = paceLabel(track.sport, units)
  return usesSpeed(track.sport)
    ? [`${formatPace(lo, track.sport, units)} ${unit}`, `${formatPace(hi, track.sport, units)} ${unit}`]
    : [`${formatPace(lo, track.sport, units)}${unit}`, `${formatPace(hi, track.sport, units)}${unit}`]
}

/** What colors the track, and the key that reads the colors back. */
export function ColorKey({ track, units, colorBy, onChange }: ColorKeyProps) {
  const [low, high] = ends(track, colorBy, units)
  const lowWord = colorBy === "pace" ? "Slower" : "Lower"
  const highWord = colorBy === "pace" ? "Faster" : "Higher"
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium">Track color</span>
        <ToggleGroup
          value={[colorBy]}
          onValueChange={(value: string[]) => {
            if (value[0]) onChange(value[0] as ColorBy)
          }}
          variant="outline"
          size="sm"
          aria-label="Color the track by"
        >
          <ToggleGroupItem value="pace" className="h-9 px-3">
            {usesSpeed(track.sport) ? "Speed" : "Pace"}
          </ToggleGroupItem>
          <ToggleGroupItem value="heart" className="h-9 px-3" disabled={!track.hr}>
            Heart
          </ToggleGroupItem>
          <ToggleGroupItem value="elevation" className="h-9 px-3" disabled={!track.ele}>
            Height
          </ToggleGroupItem>
        </ToggleGroup>
      </div>
      <div className="flex flex-col gap-1">
        <div className="ramp-bar h-2 rounded-full" aria-hidden="true" />
        <div className="flex justify-between text-xs text-muted-foreground tabular-nums">
          <span>
            {lowWord} <span className="text-foreground">{low}</span>
          </span>
          <span>
            <span className="text-foreground">{high}</span> {highWord}
          </span>
        </div>
      </div>
    </div>
  )
}
