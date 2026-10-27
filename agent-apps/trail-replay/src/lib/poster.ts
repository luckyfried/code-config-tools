import { distanceUnit, formatCoordinate, formatDate, formatDistance, formatDuration, formatHeight, heightUnit } from "./format"
import { cssVar, resolveColor, rgba } from "./tokens"
import type { Track, Units } from "./types"

export interface PosterOptions {
  title: string
  subtitle: string
  paper: "light" | "dark"
  profile: boolean
  units: Units
}

export const POSTER_RATIO = 2 / 3
const DISPLAY = '"Big Shoulders Display Variable", "Arial Narrow", sans-serif'
const SANS = '"Geist Variable", ui-sans-serif, system-ui, sans-serif'

export async function posterFonts() {
  await Promise.all([document.fonts.load(`700 100px ${DISPLAY}`), document.fonts.load(`500 40px ${SANS}`), document.fonts.load(`400 40px ${SANS}`)])
}

/** A seeded random, so the grain on the preview and the download is the same paper. */
function seeded(seed: number) {
  let s = seed % 2147483647
  if (s <= 0) s += 2147483646
  return () => (s = (s * 16807) % 2147483647) / 2147483647
}

function grain(ink: [number, number, number, number], paperIsDark: boolean) {
  const size = 256
  const tile = new OffscreenCanvas(size, size)
  const g = tile.getContext("2d")!
  const image = g.createImageData(size, size)
  const random = seeded(7)
  for (let i = 0; i < image.data.length; i += 4) {
    const r = random()
    image.data[i] = ink[0]
    image.data[i + 1] = ink[1]
    image.data[i + 2] = ink[2]
    image.data[i + 3] = r > 0.5 ? Math.round((r - 0.5) * (paperIsDark ? 34 : 26)) : 0
  }
  g.putImageData(image, 0, 0)
  return tile
}

function mercator(lat: number, lon: number): [number, number] {
  const x = (lon + 180) / 360
  const s = Math.sin((lat * Math.PI) / 180)
  return [x, 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI)]
}

function fitText(ctx: OffscreenCanvasRenderingContext2D | CanvasRenderingContext2D, text: string, font: (size: number) => string, size: number, max: number) {
  let s = size
  ctx.font = font(s)
  while (ctx.measureText(text).width > max && s > size * 0.45) {
    s *= 0.94
    ctx.font = font(s)
  }
  return s
}

/** Draws the poster: the route as one line on the theme's paper, with the distance, time, and climb in the display face. */
export function drawPoster(canvas: HTMLCanvasElement | OffscreenCanvas, track: Track, options: PosterOptions) {
  const ctx = canvas.getContext("2d") as CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D
  const W = canvas.width
  const H = canvas.height
  const tone = options.paper
  const paper = resolveColor(cssVar(`poster-${tone}-paper`))
  const ink = resolveColor(cssVar(`poster-${tone}-ink`))
  const line = resolveColor(cssVar(`poster-${tone}-line`))
  const muted = resolveColor(cssVar(`poster-${tone}-muted`))
  const u = W / 1000
  const margin = 90 * u

  ctx.save()
  ctx.fillStyle = rgba(paper)
  ctx.fillRect(0, 0, W, H)

  // Paper: fine grain, a few long fibers, and edges a shade deeper than the middle.
  const pattern = ctx.createPattern(grain(tone === "dark" ? [255, 255, 255, 1] : ink, tone === "dark"), "repeat")
  if (pattern) {
    ctx.fillStyle = pattern
    ctx.fillRect(0, 0, W, H)
  }
  const random = seeded(23)
  ctx.lineWidth = 0.6 * u
  for (let i = 0; i < 140; i++) {
    const x = random() * W
    const y = random() * H
    const a = random() * Math.PI
    const len = (10 + random() * 40) * u
    ctx.strokeStyle = rgba(tone === "dark" ? [255, 255, 255, 1] : ink, 0.035 + random() * 0.03)
    ctx.beginPath()
    ctx.moveTo(x, y)
    ctx.quadraticCurveTo(x + Math.cos(a) * len * 0.5 + random() * 4 * u, y + Math.sin(a) * len * 0.5, x + Math.cos(a) * len, y + Math.sin(a) * len)
    ctx.stroke()
  }
  const vignette = ctx.createRadialGradient(W / 2, H * 0.45, W * 0.3, W / 2, H / 2, W * 0.95)
  vignette.addColorStop(0, rgba([0, 0, 0, 1], 0))
  vignette.addColorStop(1, rgba([0, 0, 0, 1], tone === "dark" ? 0.28 : 0.07))
  ctx.fillStyle = vignette
  ctx.fillRect(0, 0, W, H)

  // Header: the date on the left, where it started on the right.
  ctx.fillStyle = rgba(muted)
  ctx.font = `500 ${19 * u}px ${SANS}`
  ctx.textBaseline = "alphabetic"
  ctx.textAlign = "left"
  ctx.fillText(formatDate(track.start), margin, margin + 10 * u)
  ctx.textAlign = "right"
  ctx.fillText(formatCoordinate(track.lat[0], track.lon[0]), W - margin, margin + 10 * u)

  // The route, fitted into the upper field.
  const top = margin + 70 * u
  const bottom = H * (options.profile ? 0.6 : 0.66)
  const boxW = W - margin * 2
  const boxH = bottom - top
  const pts = track.lat.map((lat, i) => mercator(lat, track.lon[i]))
  let minX = Infinity
  let maxX = -Infinity
  let minY = Infinity
  let maxY = -Infinity
  for (const [x, y] of pts) {
    minX = Math.min(minX, x)
    maxX = Math.max(maxX, x)
    minY = Math.min(minY, y)
    maxY = Math.max(maxY, y)
  }
  const scale = Math.min(boxW / (maxX - minX || 1e-9), boxH / (maxY - minY || 1e-9)) * 0.92
  const ox = margin + (boxW - (maxX - minX) * scale) / 2
  const oy = top + (boxH - (maxY - minY) * scale) / 2
  const px = (x: number) => ox + (x - minX) * scale
  const py = (y: number) => oy + (y - minY) * scale
  const weight = 4.2 * u
  ctx.strokeStyle = rgba(line)
  ctx.lineWidth = weight
  ctx.lineCap = "round"
  ctx.lineJoin = "round"
  ctx.beginPath()
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(px(x), py(y)) : ctx.moveTo(px(x), py(y))))
  ctx.stroke()
  const [sx, sy] = pts[0]
  ctx.fillStyle = rgba(ink)
  ctx.beginPath()
  ctx.arc(px(sx), py(sy), weight * 2, 0, Math.PI * 2)
  ctx.fill()
  const [ex, ey] = pts[pts.length - 1]
  if (Math.hypot(px(ex) - px(sx), py(ey) - py(sy)) > weight * 6) {
    ctx.strokeStyle = rgba(ink)
    ctx.lineWidth = weight * 0.8
    ctx.beginPath()
    ctx.arc(px(ex), py(ey), weight * 2, 0, Math.PI * 2)
    ctx.stroke()
  }

  // The elevation profile, in the same line weight.
  let y = bottom + 40 * u
  if (options.profile && track.ele) {
    const band = 90 * u
    const total = track.d[track.d.length - 1]
    let lo = Infinity
    let hi = -Infinity
    for (const e of track.ele) {
      lo = Math.min(lo, e)
      hi = Math.max(hi, e)
    }
    ctx.strokeStyle = rgba(ink, 0.8)
    ctx.lineWidth = weight * 0.55
    ctx.beginPath()
    const step = Math.max(1, Math.floor(track.ele.length / 600))
    for (let i = 0; i < track.ele.length; i += step) {
      const x = margin + (track.d[i] / total) * boxW
      const yy = y + band - ((track.ele[i] - lo) / (hi - lo || 1)) * band
      if (i === 0) ctx.moveTo(x, yy)
      else ctx.lineTo(x, yy)
    }
    ctx.stroke()
    ctx.fillStyle = rgba(muted)
    ctx.font = `400 ${16 * u}px ${SANS}`
    ctx.textAlign = "left"
    ctx.fillText(`${formatHeight(lo, options.units)} ${heightUnit(options.units)}`, margin, y + band + 26 * u)
    ctx.textAlign = "right"
    ctx.fillText(`${formatHeight(hi, options.units)} ${heightUnit(options.units)} high point`, W - margin, y + band + 26 * u)
    y += band + 60 * u
  }

  // A hairline, then the title and who went.
  ctx.strokeStyle = rgba(ink, 0.25)
  ctx.lineWidth = Math.max(1, 1.2 * u)
  ctx.beginPath()
  ctx.moveTo(margin, y)
  ctx.lineTo(W - margin, y)
  ctx.stroke()
  y += 92 * u
  ctx.fillStyle = rgba(ink)
  ctx.textAlign = "left"
  const titleSize = fitText(ctx, options.title, (s) => `700 ${s}px ${DISPLAY}`, 96 * u, boxW)
  ctx.font = `700 ${titleSize}px ${DISPLAY}`
  ctx.fillText(options.title, margin, y)
  y += 42 * u
  ctx.fillStyle = rgba(muted)
  ctx.font = `400 ${21 * u}px ${SANS}`
  ctx.fillText(options.subtitle, margin, y)

  // The three numbers, set along the bottom margin.
  const s = track.summary
  const stats: [string, string][] = [
    [formatDistance(s.distance, options.units), distanceUnit(options.units) === "km" ? "kilometers" : "miles"],
    [formatDuration(s.moving), "moving time"],
    [formatHeight(s.climb, options.units), options.units === "km" ? "meters climbed" : "feet climbed"],
  ]
  const base = H - margin - 34 * u
  const col = boxW / 3
  stats.forEach(([value, label], i) => {
    const x = margin + col * i
    ctx.fillStyle = rgba(ink)
    ctx.textAlign = "left"
    const size = fitText(ctx, value, (z) => `700 ${z}px ${DISPLAY}`, 104 * u, col - 24 * u)
    ctx.font = `700 ${size}px ${DISPLAY}`
    ctx.fillText(value, x, base)
    ctx.fillStyle = rgba(muted)
    ctx.font = `500 ${19 * u}px ${SANS}`
    ctx.fillText(label, x, base + 30 * u)
  })
  ctx.restore()
}

export async function downloadPoster(track: Track, options: PosterOptions) {
  await posterFonts()
  const canvas = document.createElement("canvas")
  canvas.width = 2400
  canvas.height = 3600
  drawPoster(canvas, track, options)
  const blob = await new Promise<Blob | null>((done) => canvas.toBlob(done, "image/png"))
  if (!blob) return
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = `${track.id}-poster.png`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
