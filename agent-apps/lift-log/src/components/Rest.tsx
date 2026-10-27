import { useEffect, useMemo, useState, type CSSProperties } from "react"
import { TimerIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import { chime } from "@/lib/chime"
import { useLog } from "@/lib/log-context"
import { stopRest, useRest } from "@/lib/store"

const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`

/** The thin bar across the very top that drains over the rest and ends on a chime. */
export function RestBar() {
  const rest = useRest()
  const { chimeOn } = useLog()

  useEffect(() => {
    if (!rest) return
    const t = window.setTimeout(() => {
      if (!rest.quiet && chimeOn) chime()
      stopRest()
    }, Math.max(0, rest.endsAt - Date.now()))
    return () => clearTimeout(t)
  }, [rest, chimeOn])

  // Where the bar starts: full for a fresh rest, part drained for one picked up after a reload.
  const offset = useMemo(() => (rest ? Math.max(0, rest.total - (rest.endsAt - Date.now()) / 1000) : 0), [rest])
  if (!rest) return null
  return (
    <div className="rest-bar" role="presentation">
      <div
        key={rest.endsAt}
        className="rest-bar__fill"
        style={{ "--rest-total": `${rest.total}s`, "--rest-offset": `${-offset}s` } as CSSProperties}
      />
    </div>
  )
}

/** The rest left, as a clock; a tap ends it. */
export function RestPill({ className }: { className?: string }) {
  const rest = useRest()
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    if (!rest) return
    const t = window.setInterval(() => setNow(Date.now()), 250)
    return () => clearInterval(t)
  }, [rest])
  if (!rest) return null
  const left = Math.max(0, Math.ceil((rest.endsAt - now) / 1000))
  return (
    <button
      type="button"
      onClick={stopRest}
      className={cn(
        "press inline-flex h-11 shrink-0 items-center gap-1.5 rounded-full bg-secondary pr-4 pl-3 text-secondary-foreground hover:bg-accent",
        className,
      )}
      aria-label={`Resting, ${left} seconds left. End the rest`}
    >
      <TimerIcon className="size-4 text-muted-foreground" />
      <span className="figures text-base font-semibold">{clock(left)}</span>
    </button>
  )
}
