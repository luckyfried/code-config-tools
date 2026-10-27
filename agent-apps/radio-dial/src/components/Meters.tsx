import { useEffect, useRef } from 'react'
import type { RadioEngine } from '@/lib/engine'
import { onFrame } from '@/lib/loop'
import { bins, levels } from '@/lib/signal-bus'
import { synth } from '@/lib/signal'
import { Spring } from '@/lib/spring'
import { cn } from '@/lib/utils'

type Props = {
  engine: RadioEngine
  seed: string
  strength: number
  className?: string
}

// Where each VU mark sits along the arc, from -20 at the left stop to +3 at the right.
const MARKS: [string, number, boolean][] = [
  ['20', 0, true],
  ['10', 0.25, true],
  ['7', 0.37, true],
  ['5', 0.47, true],
  ['3', 0.59, true],
  ['2', 0.66, false],
  ['1', 0.73, false],
  ['0', 0.8, true],
  ['1', 0.87, false],
  ['2', 0.93, false],
  ['3', 1, true],
]
const RED_FROM = 0.8
const SWING = (50 * Math.PI) / 180

type Palette = { ink: string; red: string; needle: string; bar: string; peak: string; soft: string }

function readPalette(el: HTMLElement): Palette {
  const css = getComputedStyle(el)
  const v = (name: string) => css.getPropertyValue(name).trim() || '#888'
  return {
    ink: v('--meter-ink'),
    red: v('--meter-red'),
    needle: v('--meter-needle'),
    bar: v('--spectrum-bar'),
    peak: v('--spectrum-peak'),
    soft: v('--scale-ink-soft'),
  }
}

type Surface = { canvas: HTMLCanvasElement; ctx: CanvasRenderingContext2D; w: number; h: number; dpr: number; face?: HTMLCanvasElement }

function fit(canvas: HTMLCanvasElement, s: Surface | null): Surface | null {
  const w = canvas.clientWidth
  const h = canvas.clientHeight
  if (!w || !h) return null
  const dpr = Math.min(2, window.devicePixelRatio || 1)
  if (s && s.w === w && s.h === h && s.dpr === dpr) return s
  canvas.width = Math.round(w * dpr)
  canvas.height = Math.round(h * dpr)
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  return { canvas, ctx, w, h, dpr }
}

function vuGeometry(w: number, h: number) {
  const r = Math.min(w * 0.6, h * 0.98)
  return { cx: w / 2, cy: h * 0.96 + r * 0.12, r }
}

function drawFace(s: Surface, p: Palette, label: string) {
  const face = document.createElement('canvas')
  face.width = s.canvas.width
  face.height = s.canvas.height
  const c = face.getContext('2d')!
  c.scale(s.dpr, s.dpr)
  const { cx, cy, r } = vuGeometry(s.w, s.h)
  const at = (f: number) => -Math.PI / 2 - SWING + f * SWING * 2
  c.lineCap = 'round'
  c.lineWidth = 1.4
  c.strokeStyle = p.ink
  c.beginPath()
  c.arc(cx, cy, r * 0.78, at(0), at(RED_FROM))
  c.stroke()
  c.strokeStyle = p.red
  c.lineWidth = 3.2
  c.beginPath()
  c.arc(cx, cy, r * 0.78, at(RED_FROM), at(1))
  c.stroke()
  const size = Math.max(9, Math.min(13, s.h * 0.12))
  c.font = `500 ${size}px "Barlow Condensed", sans-serif`
  c.textAlign = 'center'
  c.textBaseline = 'middle'
  for (const [text, f, major] of MARKS) {
    const a = at(f)
    const red = f > RED_FROM
    c.strokeStyle = red ? p.red : p.ink
    c.lineWidth = major ? 1.6 : 1
    const r0 = r * 0.78
    const r1 = r * (major ? 0.9 : 0.85)
    c.beginPath()
    c.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0)
    c.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1)
    c.stroke()
    if (major) {
      c.fillStyle = red ? p.red : p.ink
      c.fillText(text, cx + Math.cos(a) * r * 1.0, cy + Math.sin(a) * r * 1.0)
    }
  }
  c.fillStyle = p.ink
  c.font = `600 ${Math.round(size * 1.35)}px "Barlow Condensed", sans-serif`
  c.fillText('VU', cx, cy - r * 0.42)
  c.font = `500 ${size}px "Barlow Condensed", sans-serif`
  c.textAlign = 'left'
  c.fillText(label, 8, s.h - size * 0.9)
  s.face = face
}

function drawNeedle(s: Surface, p: Palette, f: number) {
  const { ctx: c, dpr } = s
  c.setTransform(1, 0, 0, 1, 0, 0)
  c.clearRect(0, 0, s.canvas.width, s.canvas.height)
  if (s.face) c.drawImage(s.face, 0, 0)
  c.setTransform(dpr, 0, 0, dpr, 0, 0)
  const { cx, cy, r } = vuGeometry(s.w, s.h)
  const a = -Math.PI / 2 - SWING + Math.max(-0.04, Math.min(1.04, f)) * SWING * 2
  c.strokeStyle = p.needle
  c.lineWidth = 1.6
  c.lineCap = 'round'
  c.beginPath()
  c.moveTo(cx + Math.cos(a) * r * 0.18, cy + Math.sin(a) * r * 0.18)
  c.lineTo(cx + Math.cos(a) * r * 0.95, cy + Math.sin(a) * r * 0.95)
  c.stroke()
}

// Two VU needles and the spectrum glass. The analyser drives them when the stream allows it; otherwise the
// breathing pulse does, so the panel never goes still.
export function Meters({ engine, seed, strength, className }: Props) {
  const leftRef = useRef<HTMLCanvasElement>(null)
  const rightRef = useRef<HTMLCanvasElement>(null)
  const specRef = useRef<HTMLCanvasElement>(null)
  const props = useRef({ seed, strength })
  props.current = { seed, strength }

  useEffect(() => {
    const root = leftRef.current?.closest('[data-panel]') as HTMLElement | null
    let palette = readPalette(root ?? document.documentElement)
    let left: Surface | null = null
    let right: Surface | null = null
    let spec: Surface | null = null
    const needles = [new Spring(0, 170, 12), new Spring(0, 150, 11)]
    const shown = new Float32Array(bins.length)
    const peaks = new Float32Array(bins.length)
    let power = 0
    let dirty = true

    const resize = () => (dirty = true)
    const ro = new ResizeObserver(resize)
    for (const c of [leftRef.current, rightRef.current, specRef.current]) if (c) ro.observe(c)
    const scheme = window.matchMedia('(prefers-color-scheme: dark)')
    const recolor = () => {
      palette = readPalette(root ?? document.documentElement)
      dirty = true
    }
    scheme.addEventListener('change', recolor)
    void document.fonts?.ready.then(recolor)

    const stop = onFrame((dt, t) => {
      if (dirty) {
        dirty = false
        if (leftRef.current) left = fit(leftRef.current, left)
        if (rightRef.current) right = fit(rightRef.current, right)
        if (specRef.current) spec = fit(specRef.current, spec)
        if (left) drawFace(left, palette, 'L')
        if (right) drawFace(right, palette, 'R')
      }
      const { seed, strength } = props.current
      power += (strength - power) * Math.min(1, dt * (strength > power ? 1.6 : 4))
      if (!engine.read(levels, bins)) synth(t, seed, power, levels, bins)

      needles.forEach((n, i) => {
        n.target = levels[i]
        n.step(dt)
      })
      if (left) drawNeedle(left, palette, needles[0].value)
      if (right) drawNeedle(right, palette, needles[1].value)

      if (spec) {
        const { ctx: c, w, h, dpr } = spec
        c.setTransform(dpr, 0, 0, dpr, 0, 0)
        c.clearRect(0, 0, w, h)
        const n = bins.length
        const pad = 10
        const gap = Math.max(2, w / n / 4)
        const bw = (w - pad * 2 - gap * (n - 1)) / n
        const floor = h - pad
        const top = pad + 2
        const grad = c.createLinearGradient(0, floor, 0, top)
        grad.addColorStop(0, palette.bar)
        grad.addColorStop(1, palette.peak)
        for (let b = 0; b < n; b++) {
          const v = bins[b]
          shown[b] += (v - shown[b]) * Math.min(1, dt * (v > shown[b] ? 22 : 7))
          peaks[b] = Math.max(shown[b], peaks[b] - dt * 0.45)
          const x = pad + b * (bw + gap)
          const bh = Math.max(1.5, Math.min(1, shown[b] * 1.25) * (floor - top))
          c.globalAlpha = 0.9
          c.fillStyle = grad
          c.fillRect(x, floor - bh, bw, bh)
          c.globalAlpha = 1
          c.fillStyle = palette.peak
          c.fillRect(x, floor - Math.max(bh, Math.min(1, peaks[b] * 1.25) * (floor - top)) - 3, bw, 2)
        }
        c.globalAlpha = 0.5
        c.fillStyle = palette.soft
        c.fillRect(pad, floor + 2, w - pad * 2, 1)
        c.globalAlpha = 1
      }
    })
    return () => {
      stop()
      ro.disconnect()
      scheme.removeEventListener('change', recolor)
    }
  }, [engine])

  return (
    <div className={cn('grid grid-cols-2 gap-3 lg:grid-cols-[1fr_1.7fr_1fr]', className)}>
      <div className="vu relative overflow-hidden rounded-[var(--radius)]">
        <span className="vu-lit" />
        <canvas ref={leftRef} className="relative block h-full w-full" aria-label="Left channel level" role="img" />
      </div>
      <div className="spectrum relative order-last col-span-2 overflow-hidden rounded-[var(--radius)] lg:order-none lg:col-span-1">
        <canvas ref={specRef} className="relative block h-full w-full" aria-label="Spectrum" role="img" />
      </div>
      <div className="vu relative overflow-hidden rounded-[var(--radius)]">
        <span className="vu-lit" />
        <canvas ref={rightRef} className="relative block h-full w-full" aria-label="Right channel level" role="img" />
      </div>
    </div>
  )
}
