import { useLayoutEffect, useMemo, useRef, type KeyboardEvent, type PointerEvent } from "react"
import { color } from "@/lib/tokens"

type Props = {
  hue: number
  chroma: number
  onChange: (hue: number) => void
}

const RING_LIGHTNESS = 0.7

/** The brand hue as a wheel: drag anywhere on it, or use the arrow keys once it has focus. */
export function HueWheel({ hue, chroma, onChange }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const gradient = useMemo(() => {
    const stops = Array.from({ length: 37 }, (_, i) => color(RING_LIGHTNESS, chroma, i * 10).hex)
    return `conic-gradient(from 0deg, ${stops.join(", ")})`
  }, [chroma])
  const thumb = color(RING_LIGHTNESS, chroma, hue).hex

  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.setProperty("--wheel", gradient)
  }, [gradient])
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.setProperty("--hue", `${hue}deg`)
    el.style.setProperty("--thumb-fill", thumb)
  }, [hue, thumb])

  const fromPointer = (event: PointerEvent<HTMLDivElement>) => {
    const box = event.currentTarget.getBoundingClientRect()
    const dx = event.clientX - (box.left + box.width / 2)
    const dy = event.clientY - (box.top + box.height / 2)
    const angle = (Math.atan2(dx, -dy) * 180) / Math.PI
    onChange(Number((((angle % 360) + 360) % 360).toFixed(1)))
  }

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const step = event.shiftKey ? 10 : 1
    const moves: Record<string, number> = {
      ArrowRight: step,
      ArrowUp: step,
      ArrowLeft: -step,
      ArrowDown: -step,
      PageUp: 15,
      PageDown: -15,
    }
    if (event.key in moves) onChange((((Math.round(hue) + moves[event.key]) % 360) + 360) % 360)
    else if (event.key === "Home") onChange(0)
    else if (event.key === "End") onChange(359)
    else return
    event.preventDefault()
  }

  return (
    <div
      ref={ref}
      className="hue-wheel"
      data-live="brand"
      role="slider"
      tabIndex={0}
      aria-label="Brand hue"
      aria-valuemin={0}
      aria-valuemax={360}
      aria-valuenow={Math.round(hue)}
      aria-valuetext={`${Math.round(hue)} degrees`}
      onKeyDown={onKeyDown}
      onPointerDown={(event) => {
        if (event.button !== 0) return
        event.currentTarget.setPointerCapture(event.pointerId)
        fromPointer(event)
      }}
      onPointerMove={(event) => {
        if (event.currentTarget.hasPointerCapture(event.pointerId)) fromPointer(event)
      }}
    >
      <div className="hue-wheel-ring" />
      <div className="hue-wheel-core">
        <div className="hue-wheel-swatch">
          <span className="text-[0.6875rem] font-medium opacity-80">Hue</span>
          <span className="text-2xl font-semibold tabular-nums">{Math.round(hue)}°</span>
        </div>
      </div>
      <div className="hue-wheel-arm">
        <span className="hue-wheel-thumb" />
      </div>
    </div>
  )
}
