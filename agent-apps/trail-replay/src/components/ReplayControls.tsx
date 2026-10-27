import { useEffect, useMemo, useRef, useSyncExternalStore } from "react"
import { PauseIcon, PlayIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { defaultRate, RATES, type ReplayClock } from "@/lib/clock"
import { formatDuration } from "@/lib/format"
import { cn } from "@/lib/utils"

interface ReplayControlsProps {
  clock: ReplayClock
  className?: string
}

function usePlaying(clock: ReplayClock) {
  return useSyncExternalStore(
    (fn) => clock.onState(fn),
    () => clock.playing,
  )
}

function useRate(clock: ReplayClock) {
  return useSyncExternalStore(
    (fn) => clock.onState(fn),
    () => clock.rate,
  )
}

/** The four speeds around the one this activity opened with. */
function choices(rate: number) {
  const at = Math.max(0, RATES.indexOf(rate))
  const start = Math.min(Math.max(0, at - 1), RATES.length - 4)
  return RATES.slice(start, start + 4)
}

/** Play and pause, the elapsed clock, a progress bar you can drag, and the replay speed. */
function useDuration(clock: ReplayClock) {
  return useSyncExternalStore(
    (fn) => clock.onState(fn),
    () => clock.duration,
  )
}

export function ReplayControls({ clock, className }: ReplayControlsProps) {
  const playing = usePlaying(clock)
  const duration = useDuration(clock)
  const rate = useRate(clock)
  const bar = useRef<HTMLDivElement>(null)
  const fill = useRef<HTMLDivElement>(null)
  const elapsed = useRef<HTMLSpanElement>(null)
  const offered = useMemo(() => choices(defaultRate(duration)), [duration])

  useEffect(() => {
    let shown = ""
    const show = (t: number) => {
      const f = t / clock.duration
      fill.current?.style.setProperty("--progress", String(f))
      // The bar moves every frame; the clock and the slider's spoken value on the clock's fresh frames.
      if (clock.playing && !clock.fresh) return
      const text = formatDuration(t, clock.duration >= 3600)
      if (elapsed.current && text !== shown) elapsed.current.textContent = shown = text
      bar.current?.setAttribute("aria-valuenow", String(Math.round(t)))
      bar.current?.setAttribute("aria-valuetext", formatDuration(t))
    }
    show(clock.t)
    return clock.subscribe(show)
  }, [clock, duration])

  useEffect(() => {
    const el = bar.current
    if (!el) return
    let active: number | null = null
    let wasPlaying = false
    const seek = (x: number) => {
      const rect = el.getBoundingClientRect()
      clock.seek(Math.min(1, Math.max(0, (x - rect.left) / rect.width)) * clock.duration)
    }
    const down = (event: PointerEvent) => {
      if (event.pointerType === "mouse" && event.button !== 0) return
      active = event.pointerId
      wasPlaying = clock.playing
      clock.pause()
      el.setPointerCapture(event.pointerId)
      seek(event.clientX)
    }
    const move = (event: PointerEvent) => {
      if (active === event.pointerId) seek(event.clientX)
    }
    const up = (event: PointerEvent) => {
      if (active !== event.pointerId) return
      active = null
      if (wasPlaying) clock.play()
    }
    const key = (event: KeyboardEvent) => {
      const step = clock.duration / 50
      const moves: Record<string, number> = { ArrowRight: step, ArrowUp: step, ArrowLeft: -step, ArrowDown: -step }
      if (event.key in moves) {
        event.preventDefault()
        clock.seek(clock.t + moves[event.key])
      } else if (event.key === "Home") clock.seek(0)
      else if (event.key === "End") clock.seek(clock.duration)
    }
    el.addEventListener("pointerdown", down)
    el.addEventListener("pointermove", move)
    el.addEventListener("pointerup", up)
    el.addEventListener("pointercancel", up)
    el.addEventListener("keydown", key)
    return () => {
      el.removeEventListener("pointerdown", down)
      el.removeEventListener("pointermove", move)
      el.removeEventListener("pointerup", up)
      el.removeEventListener("pointercancel", up)
      el.removeEventListener("keydown", key)
    }
  }, [clock])

  return (
    <div className={cn("flex items-center gap-3", className)}>
      <Button
        size="icon-lg"
        className="size-11 shrink-0 rounded-full"
        onClick={() => clock.toggle()}
        aria-label={playing ? "Pause the replay" : "Play the replay"}
      >
        {playing ? <PauseIcon /> : <PlayIcon />}
      </Button>
      <span className="w-[4.5rem] shrink-0 text-sm tabular-nums">
        <span ref={elapsed}>0:00</span>
        <span className="block text-xs text-muted-foreground">of {formatDuration(duration)}</span>
      </span>
      <div
        ref={bar}
        role="slider"
        tabIndex={0}
        aria-label="Replay position"
        aria-valuemin={0}
        aria-valuemax={Math.round(duration)}
        className="group relative flex h-11 min-w-0 flex-1 cursor-pointer touch-none items-center rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted-foreground/20">
          <div ref={fill} className="progress-fill absolute inset-0 origin-left rounded-full bg-primary" />
        </div>
      </div>
      <ToggleGroup
        value={[String(rate)]}
        onValueChange={(value: string[]) => {
          const next = Number(value[0])
          if (Number.isFinite(next) && next > 0) clock.setRate(next)
        }}
        variant="outline"
        size="sm"
        aria-label="Replay speed"
        className="hidden shrink-0 sm:flex short:hidden"
      >
        {offered.map((choice) => (
          <ToggleGroupItem key={choice} value={String(choice)} className="h-9 px-2.5 tabular-nums" aria-label={`${choice} times real time`}>
            {choice}×
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      <Button
        variant="outline"
        size="sm"
        className="h-9 shrink-0 tabular-nums sm:hidden short:inline-flex"
        aria-label={`Replay speed ${rate} times real time; tap for the next speed`}
        onClick={() => {
          clock.setRate(offered[(offered.indexOf(rate) + 1) % offered.length])
        }}
      >
        {rate}×
      </Button>
    </div>
  )
}
