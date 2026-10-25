import { useEffect, useId, useImperativeHandle, useRef, type Ref } from "react"
import { cn } from "@/lib/utils"
import { prefersReducedMotion, RING_EASING, RING_MS, tween } from "@/lib/motion"

export type RingKey = "calories" | "protein" | "carbs" | "fat"
export type RingValues = Record<RingKey, number>
export type RingsHandle = { pulse: (key: RingKey) => void }

type Spec = { key: RingKey; r: number; w: number; arc: number; rotate: number; base: string; mid: string; deep: string; track: string; fill: string; fillDeep: string }

/*
 * Geometry in a 200-unit box. The full size sits on a plate: the calorie dial runs round the rim, open at the
 * bottom, and protein, carbs, and fat sit in the well. Mini rings drop the plate and the end caps.
 */
const SPECS: Spec[] = [
  { key: "calories", r: 91.5, w: 8, arc: 0.75, rotate: 135, base: "", mid: "stroke-energy-mid", deep: "stroke-energy-deep", track: "stroke-energy/15", fill: "", fillDeep: "fill-energy-deep" },
  { key: "protein", r: 71, w: 15, arc: 1, rotate: -90, base: "stroke-protein", mid: "stroke-protein-mid", deep: "stroke-protein-deep", track: "stroke-protein/15", fill: "fill-protein", fillDeep: "fill-protein-deep" },
  { key: "carbs", r: 52.5, w: 15, arc: 1, rotate: -90, base: "stroke-carbs", mid: "stroke-carbs-mid", deep: "stroke-carbs-deep", track: "stroke-carbs/15", fill: "fill-carbs", fillDeep: "fill-carbs-deep" },
  { key: "fat", r: 34, w: 15, arc: 1, rotate: -90, base: "stroke-fat", mid: "stroke-fat-mid", deep: "stroke-fat-deep", track: "stroke-fat/15", fill: "fill-fat", fillDeep: "fill-fat-deep" },
]

const MINI: Record<RingKey, { r: number; w: number }> = {
  calories: { r: 93, w: 12 },
  protein: { r: 73, w: 17 },
  carbs: { r: 53, w: 17 },
  fat: { r: 33, w: 17 },
}

/* The ring's share past its target over which the whole first lap turns to the darker shade. */
const OVER_FADE = 0.03

type Parts = {
  lap1: SVGCircleElement | null
  mid: SVGCircleElement | null
  lap2: SVGCircleElement | null
  tip: SVGGElement | null
  cap: SVGCircleElement | null
}

function dash(el: SVGCircleElement | null, length: number, circumference: number) {
  if (!el) return
  el.style.setProperty("stroke-dasharray", `${length} ${circumference}`)
  el.style.setProperty("opacity", length < 0.3 ? "0" : "1")
}

type Props = {
  values: RingValues
  size?: "full" | "mini"
  /** Draw from empty on first paint, after this many milliseconds. */
  delay?: number
  className?: string
  label: string
  handle?: Ref<RingsHandle>
  children?: React.ReactNode
}

/**
 * Three macro rings inside a calorie dial. Past 100 % the first lap turns a shade darker and a second lap runs
 * over it in the deep shade, its end cap casting a shadow on the lap beneath.
 */
export function Rings({ values, size = "full", delay = 0, className, label, handle, children }: Props) {
  const uid = useId().replace(/:/g, "")
  const parts = useRef<Parts[]>([])
  const layers = useRef<(HTMLDivElement | null)[]>([])
  const shown = useRef<RingValues>({ calories: 0, protein: 0, carbs: 0, fat: 0 })
  const first = useRef(true)
  const full = size === "full"

  const geometry = SPECS.map((s) => {
    const g = full ? s : { ...s, ...MINI[s.key] }
    return { ...g, c: 2 * Math.PI * g.r }
  })

  const paint = (v: RingValues) => {
    geometry.forEach((g, i) => {
      const p = Math.max(0, v[g.key])
      const span = g.c * g.arc
      const one = span * Math.min(p, 1)
      const two = span * Math.min(Math.max(p - 1, 0), 1)
      const part = parts.current[i]
      if (!part) return
      dash(part.lap1, one, g.c)
      dash(part.lap2, two, g.c)
      part.mid?.style.setProperty("opacity", String(Math.min(1, Math.max(0, (p - 1) / OVER_FADE))))
      if (part.tip && part.cap) {
        const over = p > 1
        const len = over ? two : one
        part.tip.setAttribute("transform", `rotate(${(len / g.c) * 360} 100 100)`)
        part.tip.style.setProperty("opacity", len < 0.3 ? "0" : "1")
        if (g.key === "calories" && !over) part.cap.setAttribute("fill", `url(#${uid}-energy)`)
        else part.cap.removeAttribute("fill")
        part.cap.setAttribute("class", over ? g.fillDeep : g.fill)
      }
    })
  }

  useEffect(() => {
    const from = { ...shown.current }
    const run = () =>
      tween(RING_MS, (k) => {
        const v = { ...from }
        for (const key of Object.keys(v) as RingKey[]) v[key] = from[key] + (values[key] - from[key]) * k
        shown.current = v
        paint(v)
      })
    if (first.current) {
      first.current = false
      paint(from)
      let cancel = () => {}
      const t = window.setTimeout(() => (cancel = run()), delay)
      return () => {
        window.clearTimeout(t)
        cancel()
      }
    }
    return run()
    // paint reads geometry, which follows size; values carry the change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values.calories, values.protein, values.carbs, values.fat])

  useImperativeHandle(handle, () => ({
    pulse(key) {
      const i = geometry.findIndex((g) => g.key === key)
      const el = layers.current[i]
      if (!el || prefersReducedMotion()) return
      el.animate(
        [{ transform: "scale(1)" }, { transform: "scale(1.06)", offset: 0.35 }, { transform: "scale(1)" }],
        { duration: 640, delay: RING_MS * 0.5, easing: RING_EASING },
      )
    },
  }))

  return (
    <div role="img" aria-label={label} className={cn("relative aspect-square", className)}>
      {full && (
        <>
          <div aria-hidden="true" className="plate absolute inset-0 rounded-full" />
          <div aria-hidden="true" className="plate-well absolute inset-[11%] rounded-full" />
        </>
      )}
      {geometry.map((g, i) => {
        const set = (k: keyof Parts) => (el: SVGCircleElement | SVGGElement | null) => {
          parts.current[i] ??= { lap1: null, mid: null, lap2: null, tip: null, cap: null }
          ;(parts.current[i] as Record<keyof Parts, unknown>)[k] = el
        }
        const energy = g.key === "calories"
        /* The dial's gradient runs from left to right on screen, so it is laid along the dial's own rotation. */
        const a = (-g.rotate * Math.PI) / 180
        const ux = Math.cos(a) * 100
        const uy = Math.sin(a) * 100
        return (
          <div key={g.key} ref={(el) => void (layers.current[i] = el)} className="absolute inset-0">
            <svg viewBox="0 0 200 200" className="size-full overflow-visible" aria-hidden="true">
              {energy && (
                <defs>
                  <linearGradient id={`${uid}-energy`} gradientUnits="userSpaceOnUse" x1={100 - ux} y1={100 - uy} x2={100 + ux} y2={100 + uy}>
                    <stop offset="0" className="[stop-color:var(--macro-energy)]" />
                    <stop offset="1" className="[stop-color:var(--macro-energy-2)]" />
                  </linearGradient>
                </defs>
              )}
              {full && i === 0 && (
                <defs>
                  <radialGradient id={`${uid}-shade`}>
                    <stop offset="0.5" className="[stop-color:var(--cap-shadow)]" />
                    <stop offset="1" className="[stop-color:var(--cap-shadow)] [stop-opacity:0]" />
                  </radialGradient>
                </defs>
              )}
              <g transform={`rotate(${g.rotate} 100 100)`} fill="none" strokeWidth={g.w} strokeLinecap="round">
                <circle cx="100" cy="100" r={g.r} className={g.track} strokeDasharray={`${g.c * g.arc} ${g.c}`} />
                <circle
                  ref={set("lap1")}
                  cx="100"
                  cy="100"
                  r={g.r}
                  className={g.base}
                  stroke={energy ? `url(#${uid}-energy)` : undefined}
                  strokeDasharray={`0 ${g.c}`}
                  opacity="0"
                />
                <circle ref={set("mid")} cx="100" cy="100" r={g.r} className={g.mid} strokeDasharray={`${g.c * g.arc} ${g.c}`} opacity="0" />
                <circle ref={set("lap2")} cx="100" cy="100" r={g.r} className={g.deep} strokeDasharray={`0 ${g.c}`} opacity="0" />
                {full && (
                  <g ref={set("tip")} opacity="0">
                    <circle cx={100 + g.r} cy={100 + g.w * 0.22} r={g.w * 0.5 + 3.5} fill={`url(#${uid}-shade)`} stroke="none" />
                    <circle ref={set("cap")} cx={100 + g.r} cy="100" r={g.w / 2} stroke="none" />
                  </g>
                )}
              </g>
            </svg>
          </div>
        )
      })}
      {children}
    </div>
  )
}
