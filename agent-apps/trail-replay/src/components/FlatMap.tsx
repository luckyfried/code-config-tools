import { useEffect, useRef } from "react"
import type { ReplayClock } from "@/lib/clock"
import { cssVar, onSchemeChange, ramp, rampAt, resolveColor, rgba } from "@/lib/tokens"
import { metricValues, sampleAtTime, spread } from "@/lib/track"
import type { ColorBy, Track } from "@/lib/types"

interface FlatMapProps {
  track: Track
  clock: ReplayClock
  colorBy: ColorBy
}

function mercator(lat: number, lon: number): [number, number] {
  const s = Math.sin((lat * Math.PI) / 180)
  return [(lon + 180) / 360, 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)]
}

/** The route on a flat canvas for a browser without WebGL: the colored line, the comet, and the marker, replaying. */
export function FlatMap({ track, clock, colorBy }: FlatMapProps) {
  const box = useRef<HTMLDivElement>(null)
  const canvas = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const el = canvas.current
    const wrap = box.current
    if (!el || !wrap) return
    const ctx = el.getContext("2d")!
    const pts = track.lat.map((lat, i) => mercator(lat, track.lon[i]))
    let base: OffscreenCanvas | null = null
    let place = (_p: [number, number]): [number, number] => [0, 0]
    let ratio = 1

    const layout = () => {
      const rect = wrap.getBoundingClientRect()
      ratio = Math.min(2, window.devicePixelRatio || 1)
      el.width = Math.round(rect.width * ratio)
      el.height = Math.round(rect.height * ratio)
      const xs = pts.map((p) => p[0])
      const ys = pts.map((p) => p[1])
      const minX = Math.min(...xs)
      const minY = Math.min(...ys)
      const spanX = Math.max(...xs) - minX || 1e-9
      const spanY = Math.max(...ys) - minY || 1e-9
      const pad = 48 * ratio
      const scale = Math.min((el.width - pad * 2) / spanX, (el.height - pad * 2) / spanY)
      const ox = (el.width - spanX * scale) / 2
      const oy = (el.height - spanY * scale) / 2
      place = ([x, y]) => [ox + (x - minX) * scale, oy + (y - minY) * scale]

      base = new OffscreenCanvas(el.width, el.height)
      const g = base.getContext("2d")!
      g.fillStyle = rgba(resolveColor(cssVar("map-bg")))
      g.fillRect(0, 0, el.width, el.height)
      // A survey grid every 500 m, so the scale of the route reads.
      g.strokeStyle = rgba(resolveColor(cssVar("foreground")), 0.07)
      g.lineWidth = 1
      const meter = 1 / (40075016 * Math.cos((track.lat[0] * Math.PI) / 180))
      const gap = 500 * meter * scale
      for (let x = ox % gap; x < el.width; x += gap) {
        g.beginPath()
        g.moveTo(x, 0)
        g.lineTo(x, el.height)
        g.stroke()
      }
      for (let y = oy % gap; y < el.height; y += gap) {
        g.beginPath()
        g.moveTo(0, y)
        g.lineTo(el.width, y)
        g.stroke()
      }
      const colors = ramp()
      const values = metricValues(track, colorBy) ?? track.v
      const [lo, hi] = spread(values)
      g.lineCap = "round"
      g.lineJoin = "round"
      g.strokeStyle = rgba(resolveColor(cssVar("track-casing")), 0.35)
      g.lineWidth = 7 * ratio
      g.beginPath()
      pts.forEach((p, i) => {
        const [x, y] = place(p)
        if (i) g.lineTo(x, y)
        else g.moveTo(x, y)
      })
      g.stroke()
      g.lineWidth = 3.5 * ratio
      for (let i = 1; i < pts.length; i++) {
        const [x0, y0] = place(pts[i - 1])
        const [x1, y1] = place(pts[i])
        g.strokeStyle = rampAt(colors, (values[i] - lo) / (hi - lo))
        g.beginPath()
        g.moveTo(x0, y0)
        g.lineTo(x1, y1)
        g.stroke()
      }
      draw(clock.t)
    }

    const draw = (t: number) => {
      if (!base) return
      ctx.drawImage(base, 0, 0)
      const here = sampleAtTime(track, t)
      const comet = resolveColor(cssVar("comet"))
      const tailFrom = Math.max(0, here.i - 40)
      for (let i = tailFrom + 1; i <= here.i; i++) {
        const [x0, y0] = place(pts[i - 1])
        const [x1, y1] = place(pts[i])
        ctx.strokeStyle = rgba(comet, ((i - tailFrom) / (here.i - tailFrom + 1)) * 0.9)
        ctx.lineWidth = 6 * ratio
        ctx.beginPath()
        ctx.moveTo(x0, y0)
        ctx.lineTo(x1, y1)
        ctx.stroke()
      }
      const [mx, my] = place(mercator(here.lat, here.lon))
      ctx.fillStyle = rgba(comet, 0.35)
      ctx.beginPath()
      ctx.arc(mx, my, 14 * ratio, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = rgba(resolveColor(cssVar("marker")))
      ctx.strokeStyle = rgba(resolveColor(cssVar("marker-ring")))
      ctx.lineWidth = 3 * ratio
      ctx.beginPath()
      ctx.arc(mx, my, 6 * ratio, 0, Math.PI * 2)
      ctx.fill()
      ctx.stroke()
    }

    const resize = new ResizeObserver(layout)
    resize.observe(wrap)
    const unsubscribe = clock.subscribe(draw)
    const unscheme = onSchemeChange(layout)
    return () => {
      resize.disconnect()
      unsubscribe()
      unscheme()
    }
  }, [track, clock, colorBy])

  return (
    <div ref={box} className="absolute inset-0">
      <canvas ref={canvas} className="size-full" role="img" aria-label={`Map of ${track.name}`} />
    </div>
  )
}
