import { useEffect, useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import type { ReplayClock } from "@/lib/clock"
import { distanceUnit, formatDuration, formatHeight, formatPace, heightUnit, paceLabel, paceName, unitLength } from "@/lib/format"
import { sampleAtTime } from "@/lib/track"
import type { Track, Units } from "@/lib/types"
import { cn } from "@/lib/utils"

interface SplitsTableProps {
  track: Track
  clock: ReplayClock
  units: Units
}

/** One row per kilometer or mile, the row under the marker lit as the replay passes through it. */
export function SplitsTable({ track, clock, units }: SplitsTableProps) {
  const [current, setCurrent] = useState(0)
  const per = unitLength(units)
  const speeds = track.splits.map((s) => s.d / Math.max(1, s.t))
  const fastest = Math.max(...speeds)
  const slowest = Math.min(...speeds)

  useEffect(() => {
    let shown = -1
    const pick = (t: number) => {
      const next = Math.min(track.splits.length - 1, Math.floor(sampleAtTime(track, t).d / per))
      if (next !== shown) {
        shown = next
        setCurrent(next)
      }
    }
    pick(clock.t)
    return clock.subscribe(pick)
  }, [track, clock, per])

  return (
    <Table className="tabular-nums">
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">{distanceUnit(units) === "km" ? "Km" : "Mile"}</TableHead>
          <TableHead>
            {paceName(track.sport)} <span className="font-normal text-muted-foreground">{paceLabel(track.sport, units)}</span>
          </TableHead>
          <TableHead className="text-right">Time</TableHead>
          <TableHead className="text-right">
            Climb <span className="font-normal text-muted-foreground">{heightUnit(units)}</span>
          </TableHead>
          {track.hr ? <TableHead className="text-right">HR</TableHead> : null}
        </TableRow>
      </TableHeader>
      <TableBody>
        {track.splits.map((split, i) => {
          const speed = speeds[i]
          const share = fastest > slowest ? (speed - slowest) / (fastest - slowest) : 1
          const partial = split.d < per * 0.98
          return (
            <TableRow key={i} data-state={i === current ? "selected" : undefined} className={cn(i === current && "bg-muted")}>
              <TableCell className="font-medium">{partial ? (split.d / per).toFixed(2) : i + 1}</TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <span className="w-11">{formatPace(speed, track.sport, units)}</span>
                  <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted-foreground/15" aria-hidden="true">
                    <span className="split-bar absolute inset-y-0 left-0 w-full origin-left rounded-full bg-chart-2" data-share={share.toFixed(2)} ref={(el) => el?.style.setProperty("--share", String(0.15 + share * 0.85))} />
                  </span>
                </div>
              </TableCell>
              <TableCell className="text-right">{formatDuration(split.t)}</TableCell>
              <TableCell className="text-right">
                {split.up >= 0.5 ? `+${formatHeight(split.up, units)}` : "0"}
                {split.down >= 0.5 ? <span className="text-muted-foreground"> −{formatHeight(split.down, units)}</span> : null}
              </TableCell>
              {track.hr ? <TableCell className="text-right">{split.hr ?? "–"}</TableCell> : null}
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}
