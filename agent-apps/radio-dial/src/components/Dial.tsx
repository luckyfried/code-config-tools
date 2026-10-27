import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import type { Station } from '@/lib/config'
import { BAND_HIGH, BAND_LOW, frequency, slot } from '@/lib/dial'
import { onFrame } from '@/lib/loop'
import { reducedMotion } from '@/lib/motion'
import { Spring } from '@/lib/spring'
import { cn } from '@/lib/utils'

type Props = {
  stations: Station[]
  index: number
  failed: Set<string>
  warming: boolean
  panel: React.RefObject<HTMLElement | null>
  readout: React.RefObject<HTMLElement | null>
  onPick: (index: number) => void
  onLock: (locked: boolean) => void
}

const SPACING_PHONE = 128
const SPACING_WIDE = 190

// The dial: the needle rides a spring to the station's place on the scale. When the scale is wider than the window
// (a phone, or many stations), the needle stays in the middle and the scale slides under it; the scale then runs on
// past both ends of the band so the glass is printed edge to edge, and fades out under the bezel at each side.
export function Dial({ stations, index, failed, warming, panel, readout, onPick, onLock }: Props) {
  const windowRef = useRef<HTMLDivElement>(null)
  const stripRef = useRef<HTMLDivElement>(null)
  const needleRef = useRef<HTMLDivElement>(null)
  const hotRef = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ w: 0, h: 0 })
  const spring = useRef(new Spring(0))
  const drag = useRef<{ x: number; from: number; moved: boolean } | null>(null)
  const lock = useRef({ value: 0, locked: false })
  const onLockRef = useRef(onLock)
  onLockRef.current = onLock

  const count = stations.length
  const spacing = size.w < 640 ? SPACING_PHONE : SPACING_WIDE
  const scale = Math.max(size.w, count * spacing)
  const sliding = scale > size.w + 1
  const target = slot(index, count)
  const pad = sliding ? size.w / 2 : 0
  const stripWidth = scale + pad * 2
  const place = (p: number) => pad + p * (scale - 24) + 12
  const dragged = useRef(false)

  useLayoutEffect(() => {
    const el = windowRef.current
    if (!el) return
    const ro = new ResizeObserver(([e]) => setSize({ w: e.contentRect.width, h: e.contentRect.height }))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  useEffect(() => {
    const s = spring.current
    if (reducedMotion()) return s.snap(target)
    if (!warming) {
      s.target = target
      return
    }
    const t = window.setTimeout(() => (s.target = target), 320)
    return () => window.clearTimeout(t)
  }, [target, warming])

  useEffect(
    () =>
      onFrame((dt) => {
        const s = spring.current
        if (!drag.current) s.step(dt)
        const w = size.w
        const x = sliding ? w / 2 : place(s.value)
        if (stripRef.current) stripRef.current.style.transform = sliding ? `translate3d(${w / 2 - place(s.value)}px,0,0)` : 'none'
        if (needleRef.current) needleRef.current.style.transform = `translate3d(${x}px,0,0)`
        if (hotRef.current) hotRef.current.style.transform = `translate3d(${x}px,0,0)`
        const f = frequency(s.value)
        if (readout.current && readout.current.textContent !== f) readout.current.textContent = f
        const settled = !drag.current && s.settled && Math.abs(s.value - s.target) < 0.004
        const l = lock.current
        const goal = settled ? 1 : 0.15
        const rate = goal > l.value ? 3.2 : 12
        const next = l.value + (goal - l.value) * Math.min(1, dt * rate)
        if (Math.abs(next - l.value) > 0.001) {
          l.value = next
          panel.current?.style.setProperty('--lock', next.toFixed(3))
        }
        if (settled !== l.locked) {
          l.locked = settled
          onLockRef.current(settled)
        }
      }),
    [size.w, scale, sliding, panel, readout],
  )

  const nearest = (pos: number) => {
    let best = 0
    for (let i = 1; i < count; i++) if (Math.abs(slot(i, count) - pos) < Math.abs(slot(best, count) - pos)) best = i
    return best
  }

  const down = (e: React.PointerEvent) => {
    drag.current = { x: e.clientX, from: spring.current.value, moved: false }
  }
  const move = (e: React.PointerEvent) => {
    const d = drag.current
    if (!d) return
    const dx = e.clientX - d.x
    if (!d.moved && Math.abs(dx) < 6) return
    if (!d.moved) (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
    d.moved = true
    const span = Math.max(1, scale - 24)
    const pos = sliding ? d.from - dx / span : d.from + dx / span
    spring.current.snap(Math.min(1, Math.max(0, pos)))
  }
  const up = () => {
    const d = drag.current
    drag.current = null
    if (!d?.moved) return
    dragged.current = true
    window.setTimeout(() => (dragged.current = false), 0)
    const s = spring.current
    const i = nearest(s.value)
    s.target = slot(i, count)
    if (i !== index) onPick(i)
  }

  const base = size.h - (size.w < 640 ? 38 : 44)
  const numberSize = size.w < 640 ? 13 : 15
  const labelTop = Math.max(22, (base - 18) * 0.42)
  const ticks = []
  const perMHz = Math.max(1, scale - 24) / (BAND_HIGH - BAND_LOW)
  const reach = Math.ceil(((pad + 12) / perMHz) * 2) / 2
  for (let f = BAND_LOW - reach; f <= BAND_HIGH + reach + 0.001; f += 0.5) {
    const x = place((f - BAND_LOW) / (BAND_HIGH - BAND_LOW))
    const major = Math.abs(f % 2) < 0.01
    if (x < -20 || x > stripWidth + 20) continue
    ticks.push(
      <g key={f}>
        <line x1={x} x2={x} y1={base - (major ? 18 : 9)} y2={base} className={major ? 'dial-tick-major' : 'dial-tick'} strokeWidth={major ? 1.6 : 1} />
        {major && (
          <text x={x} y={base + numberSize + 6} textAnchor="middle" className="dial-number" fontSize={numberSize} fontWeight={500}>
            {f.toFixed(0)}
          </text>
        )}
      </g>,
    )
  }

  return (
    <div className="dial-bezel h-full rounded-[calc(var(--radius)*1.1)] p-[5px]">
      <div
        ref={windowRef}
        className="dial-window h-full rounded-[var(--radius)]"
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={up}
      >
        <div className="dial-lamp" />
        <div ref={hotRef} className="dial-hotspot" />
        <div className="dial-glass" />
        <div className={cn('dial-track', sliding && 'is-sliding')}>
        <div ref={stripRef} className="dial-strip" style={{ width: stripWidth }}>
          {size.w > 0 && (
            <svg width={stripWidth} height={size.h} className="absolute inset-0" aria-hidden="true">
              <line x1={sliding ? 0 : 12} x2={sliding ? stripWidth : scale - 12} y1={base} y2={base} className="dial-tick-major" strokeWidth={1.2} />
              {ticks}
              {stations.map((st, i) => (
                <circle key={st.id} cx={place(slot(i, count))} cy={base - 27} r={3} className={cn('dial-mark', i === index && 'is-current')} />
              ))}
            </svg>
          )}
          {stations.map((s, i) => {
            const x = place(slot(i, count))
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => !dragged.current && onPick(i)}
                className={cn(
                  'dial-station absolute -translate-x-1/2 -translate-y-1/2 truncate rounded px-1.5 text-center font-medium leading-tight uppercase tracking-[0.06em]',
                  i === index && 'is-current',
                  failed.has(s.id) && 'is-failed',
                )}
                style={{ left: x, top: labelTop, maxWidth: spacing - 6, fontSize: size.w < 640 ? 14 : 18 }}
                aria-label={`Tune to ${s.name}`}
                aria-current={i === index ? 'true' : undefined}
              >
                {s.name}
              </button>
            )
          })}
        </div>
        </div>
        <div ref={needleRef} className="dial-needle" style={{ top: labelTop + 20 }} />
        <div className="dial-sheen" />
      </div>
    </div>
  )
}
