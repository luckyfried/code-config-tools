import { useEffect, useMemo, useRef } from "react"
import type { ReplayClock } from "@/lib/clock"
import { formatDuration, formatHeight, formatWhole, formatPace, heightUnit, paceLabel, usesSpeed, distanceUnit, distanceValue } from "@/lib/format"
import { onSchemeChange, resolveColor, cssVar, rgba } from "@/lib/tokens"
import { indexAt, sampleAtTime, timeAtDistance, totalDistance } from "@/lib/track"
import type { Track, Units } from "@/lib/types"
import { cn } from "@/lib/utils"

export type Metric = "elevation" | "pace" | "heart"

interface ProfileChartProps {
  track: Track
  metric: Metric
  units: Units
  clock: ReplayClock
  className?: string
}

const COLOR: Record<Metric, string> = { elevation: "chart-1", pace: "chart-2", heart: "chart-3" }
const TITLE: Record<Metric, string> = { elevation: "Elevation", pace: "Pace", heart: "Heart rate" }

function series(track: Track, metric: Metric, units: Units): number[] | null {
  if (metric === "elevation") return track.ele ? track.ele.map((e) => (units === "km" ? e : e * 3.28084)) : null
  if (metric === "heart") {
    if (!track.hr) return null
    let last = track.hr.find((h) => h != null) ?? 0
    return track.hr.map((h) => (h == null ? last : (last = h)))
  }
  // Speed, so faster sits higher for runs and rides alike; the labels say pace where pace is the word.
  return track.v
}

function readout(metric: Metric, value: number | null, track: Track, units: Units) {
  if (value == null || !Number.isFinite(value)) return "–"
  if (metric === "elevation") return formatWhole(value)
  if (metric === "heart") return String(Math.round(value))
  return formatPace(value, track.sport, units)
}

function unitOf(metric: Metric, track: Track, units: Units) {
  if (metric === "elevation") return heightUnit(units)
  if (metric === "heart") return "bpm"
  return paceLabel(track.sport, units)
}

export function chartTitle(metric: Metric, track: Track) {
  if (metric === "pace" && usesSpeed(track.sport)) return "Speed"
  return TITLE[metric]
}

/** One profile chart on canvas: a filled line along the distance, with a cursor and a scrub handle tied to the replay. */
export function ProfileChart({ track, metric, units, clock, className }: ProfileChartProps) {
  const wrap = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)
  const handle = useRef<HTMLDivElement>(null)
  const valueText = useRef<HTMLSpanElement>(null)
  const values = useMemo(() => series(track, metric, units), [track, metric, units])

  useEffect(() => {
    const el = canvas.current
    const box = wrap.current
    if (!el || !box || !values) return
    const ctx = el.getContext("2d")!
    const total = totalDistance(track)
    let lo = Number.POSITIVE_INFINITY
    let hi = Number.NEGATIVE_INFINITY
    // Pace and heart rate ignore the stops and sprints at the edges so the line uses the height it has.
    const sorted = values.filter(Number.isFinite).toSorted((a, b) => a - b)
    if (metric === "elevation") {
      lo = sorted[0]
      hi = sorted[sorted.length - 1]
    } else {
      lo = sorted[Math.floor(sorted.length * 0.02)]
      hi = sorted[Math.floor(sorted.length * 0.99)]
    }
    const pad = (hi - lo) * 0.12 || 1
    lo -= metric === "elevation" ? pad * 0.4 : pad
    hi += pad
    let width = 0
    let height = 0
    let ratio = 1
    let dim: OffscreenCanvas | null = null
    let bright: OffscreenCanvas | null = null
    let ink = ""

    const x = (d: number) => (d / total) * width
    const y = (v: number) => {
      const clamped = Math.min(hi, Math.max(lo, v))
      return height - 4 - ((clamped - lo) / (hi - lo)) * (height - 10)
    }

    const paintLayer = (alphaTop: number, alphaLine: number) => {
      const layer = new OffscreenCanvas(width * ratio, height * ratio)
      const g = layer.getContext("2d")!
      g.scale(ratio, ratio)
      const color = resolveColor(cssVar(COLOR[metric]))
      const step = Math.max(1, Math.floor(values.length / (width * 1.5)))
      g.beginPath()
      g.moveTo(0, height)
      for (let i = 0; i < values.length; i += step) g.lineTo(x(track.d[i]), y(values[i]))
      g.lineTo(width, y(values[values.length - 1]))
      g.lineTo(width, height)
      g.closePath()
      // The fill starts at the line's highest point, so a chart whose line sits low still gets its strongest color.
      let top = height
      for (let i = 0; i < values.length; i += step) top = Math.min(top, y(values[i]))
      const fill = g.createLinearGradient(0, top, 0, height)
      fill.addColorStop(0, rgba(color, alphaTop))
      fill.addColorStop(0.55, rgba(color, alphaTop * 0.45))
      fill.addColorStop(1, rgba(color, 0.04))
      g.fillStyle = fill
      g.fill()
      g.beginPath()
      for (let i = 0; i < values.length; i += step) {
        const px = x(track.d[i])
        const py = y(values[i])
        if (i === 0) g.moveTo(px, py)
        else g.lineTo(px, py)
      }
      g.lineTo(width, y(values[values.length - 1]))
      g.strokeStyle = rgba(color, alphaLine)
      g.lineWidth = 1.75
      g.lineJoin = "round"
      g.stroke()
      return layer
    }

    const layout = () => {
      const rect = box.getBoundingClientRect()
      width = Math.max(10, Math.round(rect.width))
      height = Math.max(10, Math.round(rect.height))
      ratio = Math.min(2, window.devicePixelRatio || 1)
      el.width = width * ratio
      el.height = height * ratio
      ink = rgba(resolveColor(cssVar("foreground")))
      dim = paintLayer(0.3, 0.5)
      bright = paintLayer(0.62, 1)
      draw(clock.t, true)
    }

    let drawnAt = Number.NaN
    let shownText = ""
    let visible = true
    const draw = (t: number, force = false) => {
      if (!dim || !bright || (!visible && !force)) return
      const here = sampleAtTime(track, t)
      const cx = x(here.d)
      // The cursor moves a few pixels a second; a frame where it would not move draws nothing.
      if (!force && Math.abs(cx - drawnAt) < 0.5 / ratio) return
      drawnAt = cx
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.clearRect(0, 0, el.width, el.height)
      ctx.drawImage(dim, 0, 0)
      ctx.save()
      ctx.beginPath()
      ctx.rect(0, 0, cx * ratio, el.height)
      ctx.clip()
      ctx.drawImage(bright, 0, 0)
      ctx.restore()
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
      const i = indexAt(track.d, here.d)
      const v = values[i] + ((values[Math.min(values.length - 1, i + 1)] - values[i]) * (here.d - track.d[i])) / Math.max(1e-6, (track.d[i + 1] ?? track.d[i]) - track.d[i])
      ctx.strokeStyle = ink
      ctx.globalAlpha = 0.55
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(Math.round(cx) + 0.5, 0)
      ctx.lineTo(Math.round(cx) + 0.5, height)
      ctx.stroke()
      ctx.globalAlpha = 1
      ctx.fillStyle = ink
      ctx.beginPath()
      ctx.arc(cx, y(v), 3.5, 0, Math.PI * 2)
      ctx.fill()
      handle.current?.style.setProperty("--x", `${cx}px`)
      // The cursor moves every frame; the number and the handle's spoken value on the clock's fresh frames.
      if (!force && clock.playing && !clock.fresh) return
      const text = readout(metric, v, track, units)
      if (valueText.current && text !== shownText) valueText.current.textContent = shownText = text
      handle.current?.setAttribute("aria-valuenow", String(Math.round(here.d)))
      handle.current?.setAttribute("aria-valuetext", `${distanceValue(here.d, units).toFixed(2)} ${distanceUnit(units)}, ${formatDuration(here.t)}`)
    }

    const resize = new ResizeObserver(layout)
    resize.observe(box)
    // A chart swiped out of view in the phone's strip waits until it is back.
    const seen = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
      if (visible) draw(clock.t, true)
    })
    seen.observe(box)
    const unsubscribe = clock.subscribe((t) => draw(t))
    const unscheme = onSchemeChange(layout)
    return () => {
      resize.disconnect()
      seen.disconnect()
      unsubscribe()
      unscheme()
    }
  }, [track, metric, units, clock, values])

  // Scrubbing: a mouse drags anywhere on the chart; a finger drags the handle, and a tap on the chart jumps there.
  useEffect(() => {
    const box = wrap.current
    const grip = handle.current
    if (!box || !grip) return
    const total = totalDistance(track)
    let wasPlaying = false
    let active: number | null = null
    let tap: { x: number; y: number; id: number } | null = null

    const seekTo = (clientX: number) => {
      const rect = box.getBoundingClientRect()
      const f = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
      clock.seek(timeAtDistance(track, f * total))
    }
    const begin = (event: PointerEvent, target: HTMLElement) => {
      active = event.pointerId
      wasPlaying = clock.playing
      clock.pause()
      target.setPointerCapture(event.pointerId)
      seekTo(event.clientX)
    }
    const onBoxDown = (event: PointerEvent) => {
      if (event.target === grip) return
      if (event.pointerType === "mouse") {
        if (event.button !== 0) return
        begin(event, box)
      } else {
        tap = { x: event.clientX, y: event.clientY, id: event.pointerId }
      }
    }
    const onGripDown = (event: PointerEvent) => {
      event.stopPropagation()
      begin(event, grip)
    }
    const onMove = (event: PointerEvent) => {
      if (active === event.pointerId) seekTo(event.clientX)
      if (tap && tap.id === event.pointerId && Math.hypot(event.clientX - tap.x, event.clientY - tap.y) > 10) tap = null
    }
    const onUp = (event: PointerEvent) => {
      if (active === event.pointerId) {
        active = null
        if (wasPlaying) clock.play()
      } else if (tap && tap.id === event.pointerId) {
        seekTo(event.clientX)
        tap = null
      }
    }
    const onCancel = (event: PointerEvent) => {
      if (active === event.pointerId) {
        active = null
        if (wasPlaying) clock.play()
      }
      tap = null
    }
    const onKey = (event: KeyboardEvent) => {
      const here = sampleAtTime(track, clock.t).d
      const step = total / 100
      let next: number | null = null
      if (event.key === "ArrowRight" || event.key === "ArrowUp") next = here + step
      if (event.key === "ArrowLeft" || event.key === "ArrowDown") next = here - step
      if (event.key === "PageUp") next = here + step * 10
      if (event.key === "PageDown") next = here - step * 10
      if (event.key === "Home") next = 0
      if (event.key === "End") next = total
      if (next == null) return
      event.preventDefault()
      clock.seek(timeAtDistance(track, Math.min(total, Math.max(0, next))))
    }
    box.addEventListener("pointerdown", onBoxDown)
    grip.addEventListener("pointerdown", onGripDown)
    for (const el of [box, grip]) {
      el.addEventListener("pointermove", onMove)
      el.addEventListener("pointerup", onUp)
      el.addEventListener("pointercancel", onCancel)
    }
    grip.addEventListener("keydown", onKey)
    return () => {
      box.removeEventListener("pointerdown", onBoxDown)
      grip.removeEventListener("pointerdown", onGripDown)
      for (const el of [box, grip]) {
        el.removeEventListener("pointermove", onMove)
        el.removeEventListener("pointerup", onUp)
        el.removeEventListener("pointercancel", onCancel)
      }
      grip.removeEventListener("keydown", onKey)
    }
  }, [track, clock])

  const title = chartTitle(metric, track)
  const unit = unitOf(metric, track, units)
  const range =
    values && metric === "elevation" && track.summary.minEle != null && track.summary.maxEle != null
      ? `${formatHeight(track.summary.minEle, units)}–${formatHeight(track.summary.maxEle, units)} ${unit}`
      : metric === "heart" && track.summary.avgHr
        ? `avg ${track.summary.avgHr} bpm`
        : metric === "pace"
          ? `avg ${formatPace(track.summary.avgSpeed, track.sport, units)} ${unit}`
          : ""

  return (
    <figure className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <figcaption className="flex items-baseline gap-2 text-sm">
        <span className="font-medium">{title}</span>
        <span className="ml-auto font-display text-xl leading-none font-semibold tabular-nums">
          <span ref={valueText}>–</span>
          <span className="ml-1 font-sans text-xs font-normal text-muted-foreground">{unit}</span>
        </span>
      </figcaption>
      <div ref={wrap} className={cn("relative min-h-0 flex-1 select-none", values ? "cursor-ew-resize" : "")}>
        {values ? (
          <>
            <canvas ref={canvas} className="absolute inset-0 size-full" aria-hidden="true" />
            <div
              ref={handle}
              role="slider"
              tabIndex={0}
              aria-label={`Replay position on the ${title.toLowerCase()} chart`}
              aria-valuemin={0}
              aria-valuemax={Math.round(totalDistance(track))}
              className="scrub-handle absolute inset-y-0 -left-[22px] flex w-11 touch-none justify-center outline-none focus-visible:[&>span]:ring-2 focus-visible:[&>span]:ring-ring"
            >
              <span className="mt-auto mb-[-6px] block size-3.5 rounded-full border-2 border-background bg-foreground shadow-sm" />
            </div>
          </>
        ) : (
          <p className="flex h-full items-center justify-center rounded-md border border-dashed text-sm text-muted-foreground">
            {metric === "heart" ? "This activity has no heart rate." : "This activity has no elevation."}
          </p>
        )}
      </div>
      <p className="text-xs text-muted-foreground tabular-nums">{range}</p>
    </figure>
  )
}
