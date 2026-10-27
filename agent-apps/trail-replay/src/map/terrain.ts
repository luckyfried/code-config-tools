import { addProtocol } from "maplibre-gl"
import type { Track } from "@/lib/types"

/**
 * Terrain tiles behind the dem:// address. A tile run.py placed under terrain/ is read from there; a tile it could
 * not place is fetched from the AWS terrain tiles while the page is online; anything else is cut from the nearest
 * placed parent tile, so the map never shows a hole.
 */
const REMOTE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"

export const TERRAIN_ATTRIBUTION =
  '<a href="https://github.com/tilezen/joerd/blob/master/docs/attribution.md" target="_blank" rel="noopener">Terrain: Mapzen, USGS 3DEP, NASA SRTM, GMTED2010, ETOPO1, EU-DEM, and others</a>'

interface TileIndex {
  local: Set<string>
  online: boolean
  maxzoom: number
}

let index: Promise<TileIndex> | null = null

export function terrainIndex() {
  index ??= fetch("./terrain/tiles.json")
    .then((answer) => (answer.ok ? answer.json() : null))
    .catch(() => null)
    .then((data: { tiles: string[]; online: boolean; maxzoom: number } | null) => ({
      local: new Set(data?.tiles ?? []),
      online: data ? data.online : true,
      maxzoom: data?.maxzoom ?? 13,
    }))
  return index
}

const cache = new Map<string, Promise<ArrayBuffer>>()

function remember(key: string, load: () => Promise<ArrayBuffer>) {
  let pending = cache.get(key)
  if (!pending) {
    pending = load()
    cache.set(key, pending)
    pending.catch(() => cache.delete(key))
  }
  return pending
}

async function bytes(url: string) {
  const answer = await fetch(url)
  if (!answer.ok) throw new Error(`${answer.status}`)
  return answer.arrayBuffer()
}

function flatTile(elevation: number) {
  const canvas = new OffscreenCanvas(256, 256)
  const ctx = canvas.getContext("2d")!
  const v = Math.round(elevation + 32768)
  ctx.fillStyle = `rgb(${Math.floor(v / 256)}, ${v % 256}, 0)`
  ctx.fillRect(0, 0, 256, 256)
  return canvas.convertToBlob({ type: "image/png" }).then((blob) => blob.arrayBuffer())
}

/** A child tile cut from a parent: nearest-neighbor, so the encoded heights stay whole numbers. */
async function fromParent(z: number, x: number, y: number, tiles: TileIndex) {
  for (let up = 1; up <= z; up++) {
    const key = `${z - up}/${x >> up}/${y >> up}`
    if (!tiles.local.has(key)) continue
    const parent = await remember(key, () => bytes(`./terrain/${key}.png`))
    const image = await createImageBitmap(new Blob([parent], { type: "image/png" }))
    const size = 256 >> up
    const sx = (x - ((x >> up) << up)) * size
    const sy = (y - ((y >> up) << up)) * size
    const canvas = new OffscreenCanvas(256, 256)
    const ctx = canvas.getContext("2d")!
    ctx.imageSmoothingEnabled = false
    ctx.drawImage(image, sx, sy, Math.max(1, size), Math.max(1, size), 0, 0, 256, 256)
    image.close()
    const blob = await canvas.convertToBlob({ type: "image/png" })
    return blob.arrayBuffer()
  }
  return flatTile(0)
}

export async function terrainTile(z: number, x: number, y: number) {
  const tiles = await terrainIndex()
  const key = `${z}/${x}/${y}`
  if (tiles.local.has(key)) return remember(key, () => bytes(`./terrain/${key}.png`))
  if (tiles.online && navigator.onLine) {
    try {
      return await remember(`remote:${key}`, () =>
        bytes(REMOTE.replace("{z}", String(z)).replace("{x}", String(x)).replace("{y}", String(y))),
      )
    } catch {
      // Cut from a parent below.
    }
  }
  return remember(`cut:${key}`, () => fromParent(z, x, y, tiles))
}

let registered = false

export function registerTerrain() {
  if (registered) return
  registered = true
  addProtocol("dem", async (params) => {
    const [z, x, y] = params.url
      .replace("dem://", "")
      .split("/")
      .map((part) => Number.parseInt(part, 10))
    return { data: await terrainTile(z, x, y) }
  })
}

function tileOf(lat: number, lon: number, z: number) {
  const n = 2 ** z
  const x = Math.floor(((lon + 180) / 360) * n)
  const r = (lat * Math.PI) / 180
  const y = Math.floor(((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * n)
  return [Math.min(n - 1, Math.max(0, x)), Math.min(n - 1, Math.max(0, y))]
}

/** Warms the tiles along the route before the camera reaches them, a few at a time. */
export async function prefetchRoute(track: Track) {
  const tiles = await terrainIndex()
  if (!tiles.online) return
  const wanted: [number, number, number][] = []
  const seen = new Set<string>()
  const stride = Math.max(1, Math.floor(track.lat.length / 300))
  for (const z of [tiles.maxzoom - 1, tiles.maxzoom]) {
    for (let i = 0; i < track.lat.length; i += stride) {
      const [x, y] = tileOf(track.lat[i], track.lon[i], z)
      const key = `${z}/${x}/${y}`
      if (!seen.has(key) && !tiles.local.has(key)) {
        seen.add(key)
        wanted.push([z, x, y])
      }
    }
  }
  const queue = wanted.slice(0, 400)
  const worker = async () => {
    for (let next = queue.shift(); next; next = queue.shift()) {
      await terrainTile(...next).catch(() => undefined)
    }
  }
  await Promise.all([worker(), worker(), worker(), worker()])
}
