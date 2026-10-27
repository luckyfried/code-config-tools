import { useEffect, useRef } from "react"
import type { ReplayClock } from "@/lib/clock"
import { distanceUnit, formatDistance, formatDuration, formatHeight, formatPace, heightUnit, paceLabel, paceName } from "@/lib/format"
import { movingTimeAt, sampleAtTime } from "@/lib/track"
import type { Track, Units } from "@/lib/types"
import { cn } from "@/lib/utils"

interface TelemetryProps {
  track: Track
  clock: ReplayClock
  units: Units
  className?: string
}

/** The numbers under the marker, live: distance, moving time, pace, heart rate, and height. */
export function Telemetry({ track, clock, units, className }: TelemetryProps) {
  const refs = {
    distance: useRef<HTMLSpanElement>(null),
    time: useRef<HTMLSpanElement>(null),
    pace: useRef<HTMLSpanElement>(null),
    hr: useRef<HTMLSpanElement>(null),
    ele: useRef<HTMLSpanElement>(null),
  }

  useEffect(() => {
    const write = (t: number) => {
      // Ten updates a second reads as live without making the numbers flicker, on the same frames as the replay clock.
      if (clock.playing && !clock.fresh) return
      const s = sampleAtTime(track, t)
      if (refs.distance.current) refs.distance.current.textContent = formatDistance(s.d, units)
      if (refs.time.current) refs.time.current.textContent = formatDuration(movingTimeAt(track, t))
      if (refs.pace.current) refs.pace.current.textContent = formatPace(s.v, track.sport, units)
      if (refs.hr.current) refs.hr.current.textContent = s.hr != null ? String(Math.round(s.hr)) : "–"
      if (refs.ele.current) refs.ele.current.textContent = s.ele != null ? formatHeight(s.ele, units) : "–"
    }
    write(clock.t)
    return clock.subscribe(write)
    // The refs are stable; the subscription follows the track, clock, and units.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [track, clock, units])

  const cell = "flex min-w-0 flex-col"
  const label = "text-[11px] leading-tight whitespace-nowrap text-muted-foreground"
  const value = "font-display text-2xl leading-none font-semibold tabular-nums sm:text-[1.75rem]"
  const unit = "ml-0.5 font-sans text-xs font-normal text-muted-foreground"
  return (
    <dl className={cn("glass grid grid-cols-[repeat(4,auto)] gap-x-3 rounded-xl border px-3.5 py-2.5 shadow-sm sm:grid-cols-[repeat(5,auto)] sm:gap-x-4", className)} aria-live="off">
      <div className={cell}>
        <dt className={label}>Distance</dt>
        <dd className={value}>
          <span ref={refs.distance}>0.00</span>
          <span className={unit}>{distanceUnit(units)}</span>
        </dd>
      </div>
      <div className={cell}>
        <dt className={label}>Moving time</dt>
        <dd className={value}>
          <span ref={refs.time}>0:00</span>
        </dd>
      </div>
      <div className={cell}>
        <dt className={label}>{paceName(track.sport)}</dt>
        <dd className={value}>
          <span ref={refs.pace}>–</span>
          <span className={unit}>{paceLabel(track.sport, units)}</span>
        </dd>
      </div>
      {track.hr ? (
        <div className={cell}>
          <dt className={label}>Heart rate</dt>
          <dd className={value}>
            <span ref={refs.hr}>–</span>
            <span className={unit}>bpm</span>
          </dd>
        </div>
      ) : null}
      {track.ele ? (
        <div className={cn(cell, track.hr ? "hidden sm:flex" : "")}>
          <dt className={label}>Height</dt>
          <dd className={value}>
            <span ref={refs.ele}>–</span>
            <span className={unit}>{heightUnit(units)}</span>
          </dd>
        </div>
      ) : null}
    </dl>
  )
}
