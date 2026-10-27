import { useEffect, useId, useRef, useState, type CSSProperties } from "react"
import { cn } from "@/lib/utils"
import type { Units } from "@/lib/config"
import { fmtWeight, platesFor } from "@/lib/lift"

const KG_TONE: Record<string, string> = { "25": "red", "20": "blue", "15": "yellow", "10": "green", "5": "white", "2.5": "red", "2": "blue", "1.5": "yellow", "1.25": "chrome", "1": "green" }
const LB_TONE: Record<string, string> = { "55": "red", "45": "blue", "35": "yellow", "25": "green", "10": "white" }

// The drawing is in millimetres, seen from the side: the shaft runs in from the left, the sleeve ends at the right.
const VB_W = 800
const VB_H = 530
const MID = 262
const FLANGE = 318
const SLEEVE_START = 348
const SLEEVE_END = 768
const CLAMP_W = 30

/** A plate's size the way it is made: every 10 kg and up is 450 mm across; the change plates step down. */
function plateSize(p: number, units: Units) {
  const kg = units === "kg" ? p : p * 0.4536
  const d = kg >= 10 ? 450 : kg >= 5 ? 280 : kg >= 2.5 ? 215 : kg >= 1.2 ? 178 : 150
  return { d, t: 14 + 2.1 * kg }
}

type Drawn = { key: string; p: number; x: number; t: number; d: number; tone: string; order: number }

function layout(perSide: number[], units: Units) {
  const tones = units === "kg" ? KG_TONE : LB_TONE
  const sizes = perSide.map((p) => plateSize(p, units))
  const room = SLEEVE_END - SLEEVE_START - CLAMP_W - 12
  const stack = sizes.reduce((s, z) => s + z.t + 2, 0)
  const k = stack > room ? room / stack : 1
  let x = SLEEVE_START
  const plates: Drawn[] = perSide.map((p, i) => {
    const t = sizes[i].t * k
    const r = { key: `${i}:${p}`, p, x, t, d: sizes[i].d, tone: tones[String(p)] ?? "chrome", order: i }
    x += t + 2 * k
    return r
  })
  return { plates, end: x }
}

const reduced = () => typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches

type Props = { total: number; bar: number; plates: number[]; units: Units; size?: "md" | "lg"; intro?: boolean }

/** The bar on the platform: the plates for the weight on the stepper slide on and stop against the collar. */
export function Barbell({ total, bar, plates, units, size = "md", intro = true }: Props) {
  const uid = useId().replace(/:/g, "")
  const load = platesFor(total, bar, plates)
  const { plates: drawn, end } = layout(load.perSide, units)

  // The first load plays plate by plate, the readout counting as each one lands; later changes move at once.
  const [landed, setLanded] = useState(() => (intro && !reduced() ? 0 : Infinity))
  const opening = useRef(landed === 0)
  useEffect(() => {
    if (!opening.current) return
    const timers = drawn.map((_, i) => window.setTimeout(() => setLanded(i + 1), introDelay(i) + 380))
    timers.push(window.setTimeout(() => setLanded(Infinity), introDelay(drawn.length) + 400))
    return () => timers.forEach(clearTimeout)
    // The intro runs once, for the load the page opened on.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const counting = landed !== Infinity

  // A plate keeps the delay it got when it first went on, so a re-render never restarts its slide.
  const delays = useRef(new Map<string, number>())
  let fresh = 0
  for (const d of drawn) {
    if (delays.current.has(d.key)) continue
    delays.current.set(d.key, opening.current && counting ? (intro && !reduced() ? introDelay(d.order) : 0) : fresh++ * 80)
  }
  const signature = drawn.map((d) => d.key).join(",")
  const clampKey = `clamp|${signature}`
  if (!delays.current.has(clampKey)) delays.current.set(clampKey, opening.current && counting ? introDelay(drawn.length) : fresh * 80 + 60)

  // Plates that come off slide back out along the sleeve.
  const prev = useRef<Drawn[]>(drawn)
  const [ghosts, setGhosts] = useState<(Drawn & { gone: number })[]>([])
  useEffect(() => {
    const now = new Set(drawn.map((d) => d.key))
    const gone = prev.current.filter((d) => !now.has(d.key))
    prev.current = drawn
    for (const d of gone) delays.current.delete(d.key)
    if (!gone.length) return
    const stamp = Date.now()
    setGhosts((g) => [...g, ...gone.map((d) => ({ ...d, gone: stamp }))])
    const t = window.setTimeout(() => setGhosts((g) => g.filter((d) => d.gone !== stamp)), 380)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signature])

  const shown = counting ? bar + 2 * load.perSide.slice(0, landed).reduce((s, p) => s + p, 0) : total
  const biggest = drawn.reduce((m, d) => Math.max(m, d.d), 50)
  const words = load.belowBar
    ? `Lighter than the ${fmtWeight(bar)} ${units} bar`
    : load.perSide.length === 0
      ? `Just the ${fmtWeight(bar)} ${units} bar`
      : `${load.perSide.map(fmtWeight).join(" + ")} a side`
  const lg = size === "lg"

  return (
    <div className="stage relative overflow-hidden rounded-xl">
      <div className="relative">
        <svg
          viewBox={`0 0 ${VB_W} ${VB_H}`}
          preserveAspectRatio="xMaxYMid meet"
          className={cn("block w-full overflow-visible", lg ? "h-[clamp(220px,31vh,340px)]" : "h-auto max-h-[240px] short:max-h-[min(170px,calc(100dvh-216px))] max-md:short:max-h-[min(170px,calc(100dvh-240px))]")}
          aria-hidden
        >
          <defs>
            <linearGradient id={`${uid}-chrome`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" className="stop-chrome-lo" />
              <stop offset="0.28" className="stop-chrome-hi" />
              <stop offset="0.55" className="stop-chrome-mid" />
              <stop offset="1" className="stop-chrome-lo" />
            </linearGradient>
            <linearGradient id={`${uid}-face`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0" className="stop-shade-light" />
              <stop offset="0.35" className="stop-clear" />
              <stop offset="1" className="stop-shade-dark" />
            </linearGradient>
            <linearGradient id={`${uid}-round`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" className="stop-shade-dark" />
              <stop offset="0.07" className="stop-shade-light" />
              <stop offset="0.2" className="stop-clear" />
              <stop offset="0.8" className="stop-clear" />
              <stop offset="1" className="stop-shade-dark" />
            </linearGradient>
            <pattern id={`${uid}-knurl`} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <rect width="2" height="5" className="knurl" />
            </pattern>
            <filter id={`${uid}-soft`} x="-20%" y="-200%" width="140%" height="500%">
              <feGaussianBlur stdDeviation="9" />
            </filter>
          </defs>

          <ellipse className="floor-shadow" cx={(SLEEVE_START + end) / 2 - 40} cy={MID + biggest / 2 + 14} rx={Math.max(120, (end - FLANGE) * 0.9 + 80)} ry="11" filter={`url(#${uid}-soft)`} />

          {/* The shaft, knurled in the hands' zone, running off to the left. */}
          <rect x="-1600" y={MID - 14} width={FLANGE + 1600} height="28" fill={`url(#${uid}-chrome)`} />
          <rect x="-1600" y={MID - 14} width={FLANGE + 1520} height="28" fill={`url(#${uid}-knurl)`} />
          {/* The flange, then the sleeve the plates ride on, and its end cap. */}
          <rect x={FLANGE} y={MID - 40} width={SLEEVE_START - FLANGE} height="80" rx="4" fill={`url(#${uid}-chrome)`} />
          <rect x={SLEEVE_START} y={MID - 25} width={SLEEVE_END - SLEEVE_START} height="50" fill={`url(#${uid}-chrome)`} />
          <rect x={SLEEVE_END} y={MID - 22} width="10" height="44" rx="3" fill={`url(#${uid}-chrome)`} />
          <rect x={SLEEVE_START} y={MID - 25} width={SLEEVE_END - SLEEVE_START} height="50" className="sleeve-groove" />

          {ghosts.map((d) => (
            <g key={`${d.key}@${d.gone}`} className="plate-at" style={{ "--x": d.x } as CSSProperties}>
              <g className="plate-off" style={{ "--from": VB_W - d.x + 40 } as CSSProperties}>
                <Plate d={d} uid={uid} />
              </g>
            </g>
          ))}
          {drawn.map((d) => (
            <g key={d.key} className="plate-at" style={{ "--x": d.x } as CSSProperties}>
              <g className="plate-on" style={{ "--from": VB_W - d.x + 40, "--d": `${delays.current.get(d.key) ?? 0}ms` } as CSSProperties}>
                <Plate d={d} uid={uid} />
              </g>
            </g>
          ))}
          {drawn.length ? (
            <g className="plate-at" style={{ "--x": end + 2 } as CSSProperties}>
              <g
                key={clampKey}
                className="plate-on"
                style={{ "--from": VB_W - end + 40, "--d": `${delays.current.get(clampKey) ?? 0}ms` } as CSSProperties}
              >
                <rect x="0" y={MID - 36} width={CLAMP_W} height="72" rx="5" className="clamp" />
                <rect x="0" y={MID - 36} width={CLAMP_W} height="72" rx="5" fill={`url(#${uid}-round)`} />
                <rect x={CLAMP_W - 12} y={MID - 52} width="10" height="18" rx="3" className="clamp" />
              </g>
            </g>
          ) : null}
        </svg>

        <div className={cn("pointer-events-none absolute top-0 left-0 flex flex-col p-3", lg && "p-4")}>
          <span className="stage-label text-xs font-medium tracking-wide uppercase">On the bar</span>
          <span className={cn("stage-figure figures font-semibold tracking-tight", lg ? "text-[3.25rem] leading-[1.05]" : "text-[2.5rem] leading-[1.05] max-md:short:text-[2rem]")}>
            {fmtWeight(shown)}
            <span className="stage-label ml-1 text-lg font-medium">{units}</span>
          </span>
        </div>
      </div>
      <div className="stage-caption flex items-baseline justify-between gap-3 px-3 py-2.5" aria-live="polite">
        <p className="figures text-base font-semibold text-pretty">{words}</p>
        <p className="shrink-0 text-sm">
          {load.short > 0 ? `${fmtWeight(load.short)} ${units} short` : `${fmtWeight(bar)} ${units} bar`}
        </p>
      </div>
    </div>
  )
}

const introDelay = (i: number) => 100 + i * 130

function Plate({ d, uid }: { d: Drawn; uid: string }) {
  const y = MID - d.d / 2
  const rx = Math.min(7, d.t / 3)
  return (
    <>
      <rect x="0" y={y} width={d.t} height={d.d} rx={rx} className="plate" data-tone={d.tone} />
      <rect x="0" y={y} width={d.t} height={d.d} rx={rx} fill={`url(#${uid}-face)`} />
      <rect x="0" y={y} width={d.t} height={d.d} rx={rx} fill={`url(#${uid}-round)`} />
      <rect x={d.t * 0.18} y={y + 6} width={Math.max(1.5, d.t * 0.08)} height={d.d - 12} rx="1" className="plate-lip" />
    </>
  )
}
