import type { Map as MapLibre } from "maplibre-gl"
import { cssVar, ramp, rampAt, resolveColor, rgba, tokenNumber, type RGBA } from "@/lib/tokens"
import { metricValues, sampleAtDistance, spread } from "@/lib/track"
import type { ColorBy, Track } from "@/lib/types"

/** The glow is drawn this many times smaller and scaled up, which softens it like a blur at a fraction of the cost. */
const GLOW_SCALE = 5
/** The ramp in this many steps: too fine to see as bands, and coarse enough that neighbors share one stroke. */
const RAMP_STEPS = 48
/** The glow is soft enough that a quarter of those steps reads the same, in a quarter of the strokes. */
const GLOW_STEPS = 12
/** The comet widens and brightens toward the marker in this many steps. */
const COMET_STEPS = 14

/** Each color's runs of segments, a segment named by its end point's index. */
function groupRuns(css: string[]) {
  const groups = new Map<string, [number, number][]>()
  let i = 1
  while (i < css.length) {
    const first = i
    while (i + 1 < css.length && css[i + 1] === css[first]) i++
    const runs = groups.get(css[first]) ?? []
    runs.push([first, i])
    groups.set(css[first], runs)
    i++
  }
  return [...groups]
}

function mix(a: RGBA, b: RGBA, f: number): RGBA {
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f, 1]
}

/**
 * The track, its glow, and the comet, drawn on a canvas over the map. Each point is projected onto the terrain as
 * drawn, so the line follows the hills, and it keeps one width on screen on every slope, the far ones included.
 */
export class TrackOverlay {
  readonly canvas = document.createElement("canvas")
  private ctx = this.canvas.getContext("2d")!
  private glow = document.createElement("canvas")
  private glowCtx = this.glow.getContext("2d")!
  private width = 0
  private height = 0
  private ratio = 1
  private track: Track | null = null
  /** Each point's color along the ramp, and its ramp position for the comet's blend. */
  private colors: RGBA[] = []
  /** The track's segments grouped by color, so each color is one stroke: [color, runs of [first, last] index]. */
  private lines: [string, [number, number][]][] = []
  private glowLines: [string, [number, number][]][] = []
  private xs = new Float32Array(0)
  private ys = new Float32Array(0)
  private theme = {
    strength: 0.6,
    edge: 0.35,
    casing: [0, 0, 0, 1] as RGBA,
    comet: [255, 255, 255, 1] as RGBA,
    core: [255, 255, 255, 1] as RGBA,
    ring: [0, 0, 0, 1] as RGBA,
    background: [255, 255, 255, 1] as RGBA,
    foreground: [0, 0, 0, 1] as RGBA,
  }

  constructor() {
    this.canvas.className = "track-overlay"
    this.canvas.setAttribute("aria-hidden", "true")
  }

  setTrack(track: Track, colorBy: ColorBy) {
    this.track = track
    const palette = ramp()
    const values = metricValues(track, colorBy) ?? track.v
    const [lo, hi] = spread(values)
    const n = values.length
    this.colors = []
    const css: string[] = []
    const glowCss: string[] = []
    for (let i = 0; i < n; i++) {
      // Average a short window so single readings do not flicker the line.
      let sum = 0
      let count = 0
      for (let j = Math.max(0, i - 3); j <= Math.min(n - 1, i + 3); j++) {
        sum += values[j]
        count++
      }
      const f = Math.min(1, Math.max(0, (sum / count - lo) / (hi - lo)))
      const color = rampAt(palette, Math.round(f * RAMP_STEPS) / RAMP_STEPS)
      css.push(color)
      glowCss.push(rampAt(palette, Math.round(f * GLOW_STEPS) / GLOW_STEPS))
      this.colors.push(resolveColor(color))
    }
    this.lines = groupRuns(css)
    this.glowLines = groupRuns(glowCss)
    this.xs = new Float32Array(n)
    this.ys = new Float32Array(n)
  }

  readTheme() {
    const color = (name: string) => resolveColor(cssVar(name))
    this.theme = {
      strength: tokenNumber("track-glow-strength", 0.6),
      edge: tokenNumber("track-casing-strength", 0.35),
      casing: color("track-casing"),
      comet: color("comet"),
      core: color("marker"),
      ring: color("marker-ring"),
      background: color("background"),
      foreground: color("foreground"),
    }
  }

  resize(width: number, height: number) {
    this.ratio = Math.min(2, window.devicePixelRatio || 1)
    this.width = width
    this.height = height
    this.canvas.width = Math.max(1, Math.round(width * this.ratio))
    this.canvas.height = Math.max(1, Math.round(height * this.ratio))
    this.glow.width = Math.max(1, Math.ceil(width / GLOW_SCALE))
    this.glow.height = Math.max(1, Math.ceil(height / GLOW_SCALE))
  }

  /** Draws the whole track, and the comet from `tailD` to `headD` meters along it. */
  draw(map: MapLibre, headD: number, tailD: number, comet: boolean) {
    const track = this.track
    const ctx = this.ctx
    if (!track || !this.width) return
    const n = track.lat.length
    for (let i = 0; i < n; i++) {
      const p = map.project([track.lon[i], track.lat[i]])
      this.xs[i] = p.x
      this.ys[i] = p.y
    }
    const zoom = map.getZoom()
    const core = Math.min(7, Math.max(2.5, 3 + (zoom - 11) * 0.72))
    const { strength, edge, casing } = this.theme
    const head = sampleAtDistance(track, headD)
    const tail = sampleAtDistance(track, Math.max(0, tailD))
    const headPt = map.project([head.lon, head.lat])

    // The glow: the track's own colors, wide and soft, and the comet's burning brighter toward the marker.
    const g = this.glowCtx
    const s = 1 / GLOW_SCALE
    g.setTransform(s, 0, 0, s, 0, 0)
    g.clearRect(0, 0, this.width, this.height)
    g.lineCap = "round"
    g.lineJoin = "round"
    g.globalAlpha = 0.45
    this.strokeColored(g, core * 3.8, this.glowLines)
    g.globalAlpha = 1
    this.strokeColored(g, core * 2, this.glowLines)
    if (comet && headD > tailD) this.strokeComet(g, tail, head, headPt, (f) => [rgba(this.theme.comet, f), core * (2 + f * 4)])

    ctx.setTransform(1, 0, 0, 1, 0, 0)
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height)
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = "high"
    ctx.globalAlpha = Math.min(1, strength)
    ctx.drawImage(this.glow, 0, 0, this.canvas.width, this.canvas.height)
    ctx.globalAlpha = 1
    ctx.setTransform(this.ratio, 0, 0, this.ratio, 0, 0)
    ctx.lineCap = "round"
    ctx.lineJoin = "round"

    // A dark edge where the theme asks for one, so the line holds on pale ground, then the line in the ramp's colors.
    if (edge > 0) {
      ctx.strokeStyle = rgba(casing, edge)
      ctx.lineWidth = core + 2
      ctx.beginPath()
      for (let i = 0; i < n; i++) {
        if (i) ctx.lineTo(this.xs[i], this.ys[i])
        else ctx.moveTo(this.xs[i], this.ys[i])
      }
      ctx.stroke()
    }
    this.strokeColored(ctx, core, this.lines)

    // The start.
    ctx.fillStyle = rgba(this.theme.background)
    ctx.strokeStyle = rgba(this.theme.foreground)
    ctx.lineWidth = 3
    ctx.beginPath()
    ctx.arc(this.xs[0], this.ys[0], 5.5, 0, Math.PI * 2)
    ctx.fill()
    ctx.stroke()

    if (!comet || headD <= tailD) return
    // The comet: a tail that widens toward the marker and turns from the track's color to the comet's, with a
    // white-hot core along most of its length.
    this.strokeComet(ctx, tail, head, headPt, (f, i) => {
      const from = this.colors[i] ?? this.theme.comet
      return [rgba(mix(from, this.theme.comet, Math.min(1, f * 2))), core * (1 + f * 1.9) + 2]
    })
    this.strokeComet(ctx, tail, head, headPt, (f) => {
      const k = Math.max(0, (f - 0.15) / 0.85)
      return [rgba(mix(this.theme.comet, this.theme.core, Math.min(1, k * 1.6))), k > 0 ? core * (0.3 + k * 1.3) : 0]
    })
  }

  /** The track in its colors, one path per color. */
  private strokeColored(g: CanvasRenderingContext2D, width: number, lines: [string, [number, number][]][]) {
    g.lineWidth = width
    for (const [color, runs] of lines) {
      g.strokeStyle = color
      g.beginPath()
      for (const [first, last] of runs) {
        g.moveTo(this.xs[first - 1], this.ys[first - 1])
        for (let i = first; i <= last; i++) g.lineTo(this.xs[i], this.ys[i])
      }
      g.stroke()
    }
  }

  /** The stretch from `tail` to `head`, segment by segment, each styled by how near the marker it is (0 to 1). */
  private strokeComet(
    g: CanvasRenderingContext2D,
    tail: { i: number; d: number; lon: number; lat: number },
    head: { i: number; d: number },
    headPt: { x: number; y: number },
    style: (f: number, i: number) => [string, number],
  ) {
    const track = this.track!
    const span = Math.max(1, head.d - tail.d)
    const pts: [number, number, number, number][] = []
    const t0 = tail.i + 1
    // The tail's first point sits between two track points; it is placed along their projected segment.
    const a = tail.i
    const b = Math.min(track.d.length - 1, a + 1)
    const f0 = track.d[b] > track.d[a] ? (tail.d - track.d[a]) / (track.d[b] - track.d[a]) : 0
    pts.push([this.xs[a] + (this.xs[b] - this.xs[a]) * f0, this.ys[a] + (this.ys[b] - this.ys[a]) * f0, 0, a])
    for (let i = t0; i <= head.i; i++) pts.push([this.xs[i], this.ys[i], (track.d[i] - tail.d) / span, i])
    pts.push([headPt.x, headPt.y, 1, head.i])
    // Segments in the same step along the tail share one stroke, styled by where that step ends.
    const step = (k: number) => Math.min(COMET_STEPS - 1, Math.floor(pts[k][2] * COMET_STEPS))
    let k = 1
    while (k < pts.length) {
      const first = k
      while (k + 1 < pts.length && step(k + 1) === step(first)) k++
      const [color, width] = style(pts[k][2], pts[first][3])
      if (width > 0) {
        g.strokeStyle = color
        g.lineWidth = width
        g.beginPath()
        g.moveTo(pts[first - 1][0], pts[first - 1][1])
        for (let j = first; j <= k; j++) g.lineTo(pts[j][0], pts[j][1])
        g.stroke()
      }
      k++
    }
  }
}
