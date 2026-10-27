import { useEffect, useRef, useState } from "react"
import { MinusIcon, PlusIcon } from "lucide-react"
import { cn } from "@/lib/utils"

type Props = {
  id: string
  label: string
  unit?: string
  value: number
  format: (v: number) => string
  parse: (text: string) => number | null
  onStep: (dir: 1 | -1) => void
  onSet: (v: number) => void
  decimal?: boolean
  size?: "md" | "lg"
  /** The keyboard keys that step this value from anywhere on the page, shown beside the label. */
  keys?: string
}

/** Hold to repeat: the first repeat after 380 ms, then faster, down to 45 ms a step. */
function useHold(onStep: (dir: 1 | -1) => void) {
  const timer = useRef<number | null>(null)
  const count = useRef(0)
  const latest = useRef(onStep)
  useEffect(() => {
    latest.current = onStep
  })
  const stop = () => {
    if (timer.current !== null) clearTimeout(timer.current)
    timer.current = null
  }
  useEffect(() => stop, [])
  const start = (dir: 1 | -1) => {
    stop()
    count.current = 0
    latest.current(dir)
    const repeat = () => {
      count.current += 1
      latest.current(dir)
      timer.current = window.setTimeout(repeat, Math.max(45, 170 - count.current * 14))
    }
    timer.current = window.setTimeout(repeat, 380)
  }
  return { start, stop }
}

export function Stepper({ id, label, unit, value, format, parse, onStep, onSet, decimal, size = "md", keys }: Props) {
  const hold = useHold(onStep)
  const [draft, setDraft] = useState<string | null>(null)

  const commit = () => {
    if (draft === null) return
    const v = parse(draft)
    if (v !== null) onSet(v)
    setDraft(null)
  }

  const button = (dir: 1 | -1) => (
    <button
      type="button"
      aria-label={`${dir > 0 ? "More" : "Less"} ${label.toLowerCase()}`}
      className={cn(
        "press flex shrink-0 items-center justify-center rounded-lg bg-secondary text-secondary-foreground",
        "hover:bg-accent focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none",
        size === "lg" ? "size-14" : "size-11",
      )}
      onPointerDown={(e) => {
        if (e.button !== 0) return
        e.currentTarget.setPointerCapture?.(e.pointerId)
        hold.start(dir)
      }}
      onPointerUp={hold.stop}
      onPointerCancel={hold.stop}
      onLostPointerCapture={hold.stop}
      onContextMenu={(e) => e.preventDefault()}
      onClick={(e) => {
        // A keyboard press arrives as a click with no pointer.
        if (e.detail === 0) onStep(dir)
      }}
    >
      {dir > 0 ? <PlusIcon className="size-6" strokeWidth={2.25} /> : <MinusIcon className="size-6" strokeWidth={2.25} />}
    </button>
  )

  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <label htmlFor={id} className="flex items-baseline gap-1 px-1 text-sm text-muted-foreground">
        {label}
        {unit ? <span className="text-xs">({unit})</span> : null}
        {keys ? <kbd className="key-hint ml-auto" aria-hidden>{keys}</kbd> : null}
      </label>
      <div className="flex items-center gap-1 rounded-xl bg-surface-2 p-1 ring-1 ring-border">
        {button(-1)}
        <input
          id={id}
          data-stepper=""
          inputMode={decimal ? "decimal" : "numeric"}
          autoComplete="off"
          enterKeyHint="done"
          className={cn(
            "figures w-full min-w-0 bg-transparent text-center font-semibold tracking-tight outline-none",
            "rounded-md focus-visible:ring-2 focus-visible:ring-ring/50",
            size === "lg" ? "h-14 text-figure" : "h-11 text-[1.75rem]",
          )}
          value={draft ?? format(value)}
          onFocus={(e) => {
            setDraft(format(value))
            requestAnimationFrame(() => e.target.select())
          }}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "ArrowUp" || e.key === "ArrowDown") {
              e.preventDefault()
              e.stopPropagation()
              setDraft(null)
              onStep(e.key === "ArrowUp" ? 1 : -1)
            } else if (e.key === "Enter") {
              commit()
              e.currentTarget.blur()
            } else if (e.key === "Escape") {
              setDraft(null)
              e.currentTarget.blur()
            }
          }}
        />
        {button(1)}
      </div>
    </div>
  )
}
