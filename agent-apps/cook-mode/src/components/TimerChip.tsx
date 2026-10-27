import { BellRingIcon, PauseIcon, TimerIcon } from "lucide-react"
import { useEffect, useState, type CSSProperties, type ReactNode } from "react"
import { cn } from "@/lib/utils"
import { clock } from "@/lib/durations"
import { clearTimer, leftOf, startTimer, timerId, toggleTimer, useNow, useTimers } from "@/lib/timers"

interface TimerChipProps {
  recipeId: string
  /** The step, counted from 1. */
  step: number
  index: number
  text: string
  ms: number
  /** The index's preview: counts the pill down from when it shows, without starting a timer. */
  demo?: boolean
}

// An inline block, so its text baseline is the line's and punctuation after it sits on that baseline.
const shape =
  "relative isolate mx-[0.06em] inline-block overflow-hidden rounded-full border px-[0.6em] py-[0.18em] align-baseline font-sans text-[max(0.6em,14px)] leading-none font-semibold whitespace-nowrap nums transition-[transform,background-color,border-color] duration-150 ease-out select-none active:scale-[0.97] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
const icon = "mr-[0.32em] inline-block size-[1.05em] align-[-0.17em]"

/** How full the pill is: what is left of the current minute, or of the whole timer when it is a minute or less. */
function fillShare(left: number, durationMs: number) {
  if (left <= 0) return 0
  if (durationMs <= 60_000) return Math.min(1, left / durationMs)
  const ofMinute = left % 60_000
  return (ofMinute === 0 ? 60_000 : ofMinute) / 60_000
}

/** The running pill's face: the time in drained colors, and over it the filled part with the same time in its own colors. */
function PillFace({ left, durationMs, children }: { left: number; durationMs: number; children: ReactNode }) {
  return (
    <>
      {children}
      <span
        className="pill-fill absolute inset-0 bg-pill px-[0.6em] py-[0.18em] text-pill-foreground"
        style={{ "--left": fillShare(left, durationMs) } as CSSProperties}
        aria-hidden="true"
      >
        {children}
      </span>
    </>
  )
}

/** The preview's clock: the time since the pill showed, read four times a second. */
function useSinceShown() {
  const [shownAt] = useState(() => Date.now())
  const [at, setAt] = useState(shownAt)
  useEffect(() => {
    const interval = window.setInterval(() => setAt(Date.now()), 250)
    return () => window.clearInterval(interval)
  }, [])
  return at - shownAt
}

/** The preview joins a timer already running, so its pill shows part drained from the first frame and drains on. */
function joinedAt(ms: number) {
  return ms > 60_000 ? ms - 24_000 : Math.round(ms * 0.6)
}

function DemoPill({ ms }: { ms: number }) {
  const left = Math.max(0, joinedAt(ms) - useSinceShown())
  return (
    <span className={cn(shape, "border-pill bg-pill-drain text-pill-drain-foreground")} aria-hidden="true">
      <PillFace left={left} durationMs={ms}>
        <TimerIcon className={icon} />
        {clock(left)}
      </PillFace>
    </span>
  )
}

export function TimerChip({ recipeId, step, index, text, ms, demo = false }: TimerChipProps) {
  const id = timerId(recipeId, step, index)
  const timer = useTimers().find((entry) => entry.id === id)
  const now = useNow()

  if (demo && !timer) {
    return <DemoPill ms={ms} />
  }

  if (!timer) {
    return (
      <button
        type="button"
        className={cn(shape, "cursor-pointer border-chip-edge bg-chip text-chip-foreground hover:border-chip-foreground/40")}
        onClick={() => startTimer({ id, recipeId, step, label: `Step ${step}`, durationMs: ms })}
        aria-label={`Start a ${text} timer`}
        data-timer-start
      >
        <TimerIcon className={icon} aria-hidden="true" />
        {text}
      </button>
    )
  }

  if (timer.done) {
    return (
      <button
        type="button"
        className={cn(shape, "cursor-pointer border-transparent bg-done text-done-foreground")}
        onClick={() => clearTimer(id)}
        aria-label={`${text} timer is done. Clear it`}
      >
        <BellRingIcon className={cn(icon, "ring-done")} aria-hidden="true" />
        Done
      </button>
    )
  }

  const left = leftOf(timer, now)
  const paused = timer.endsAt === null
  return (
    <button
      type="button"
      className={cn(shape, "cursor-pointer border-pill bg-pill-drain text-pill-drain-foreground")}
      onClick={() => toggleTimer(id)}
      aria-label={`${paused ? "Resume" : "Pause"} the ${text} timer, ${clock(left)} left`}
    >
      <PillFace left={left} durationMs={timer.durationMs}>
        {paused ? <PauseIcon className={icon} aria-hidden="true" /> : <TimerIcon className={icon} aria-hidden="true" />}
        {clock(left)}
      </PillFace>
    </button>
  )
}
