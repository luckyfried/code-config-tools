import { useEffect, useRef } from "react"
import { Map as MapLibre, Marker, setWorkerUrl } from "maplibre-gl"
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url"
import "maplibre-gl/dist/maplibre-gl.css"
import type { ReplayClock } from "@/lib/clock"
import { isPhone, reducedMotion } from "@/lib/device"
import { onSchemeChange } from "@/lib/tokens"
import { headingAt, sampleAtTime, totalDistance } from "@/lib/track"
import type { ColorBy, Track } from "@/lib/types"
import { TrackOverlay } from "@/map/overlay"
import { buildStyle } from "@/map/style"
import { prefetchRoute, registerTerrain } from "@/map/terrain"

setWorkerUrl(workerUrl)

interface ReplayMapProps {
  track: Track
  clock: ReplayClock
  colorBy: ColorBy
  labels: boolean
  follow: boolean
  lite: boolean
  onUserMove: () => void
  onSlow: () => void
}

const PITCH = 60
/**
 * How far, in zoom levels, a wide map's camera may pull back to keep the track clear of the top bar and live numbers;
 * a ride covers about three times the ground of a run or a hike.
 */
const fitRange = (track: Track) => (track.sport === "ride" ? 2 : 1.25)
/** Room around the whole route when the camera holds still: clear of the title bar and the live numbers. */
const OVERVIEW = { top: 110, bottom: 150, left: 50, right: 50 }

function chaseZoom(track: Track) {
  const phone = isPhone()
  const base = track.sport === "ride" ? 13.6 : 14.55
  return phone ? base - 0.6 : base
}

/** How far the comet's tail reaches behind the marker, in meters. */
function cometLength(track: Track) {
  return Math.min(totalDistance(track) * 0.12, track.sport === "ride" ? 1200 : 450)
}

function turn(from: number, to: number) {
  return ((to - from + 540) % 360) - 180
}

interface Clear {
  top: number
  bottom: number
  left: number
  right: number
}

/**
 * How many zoom levels the camera should move so every point of the track lands inside `clear`, scaling about the
 * marker's place on screen; negative zooms out. The far side of a pitched map shrinks a little more than this, so it
 * is run again on the next frame, which settles it.
 */
function fitZoom(map: MapLibre, track: Track, at: { lon: number; lat: number }, clear: Clear) {
  const anchor = map.project([at.lon, at.lat])
  const room = {
    left: Math.max(1, anchor.x - clear.left),
    right: Math.max(1, clear.right - anchor.x),
    up: Math.max(1, anchor.y - clear.top),
    down: Math.max(1, clear.bottom - anchor.y),
  }
  let scale = 4
  const n = track.lat.length
  const stride = Math.max(1, Math.floor(n / 160))
  for (let i = 0; i < n; i += i + stride < n ? stride : Math.max(1, n - 1 - i)) {
    const p = map.project([track.lon[i], track.lat[i]])
    const dx = p.x - anchor.x
    const dy = p.y - anchor.y
    if (dx < -0.5) scale = Math.min(scale, room.left / -dx)
    if (dx > 0.5) scale = Math.min(scale, room.right / dx)
    if (dy < -0.5) scale = Math.min(scale, room.up / -dy)
    if (dy > 0.5) scale = Math.min(scale, room.down / dy)
  }
  return Math.log2(scale)
}

export function ReplayMap({ track, clock, colorBy, labels, follow, lite, onUserMove, onSlow }: ReplayMapProps) {
  const box = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibre | null>(null)
  const markerRef = useRef<Marker | null>(null)
  const live = useRef({ track, colorBy, labels, follow, lite, bearing: 0, zoom: Number.NaN, wide: false, last: 0, lastT: 0, head: 0, frames: [] as number[], slowSent: false })
  live.current.track = track
  live.current.colorBy = colorBy
  live.current.labels = labels
  live.current.follow = follow
  live.current.lite = lite
  const onUserMoveRef = useRef(onUserMove)
  const onSlowRef = useRef(onSlow)
  const drawRef = useRef<(t: number, jump?: boolean) => void>(() => undefined)
  const restyleRef = useRef<() => void>(() => undefined)
  useEffect(() => {
    onUserMoveRef.current = onUserMove
    onSlowRef.current = onSlow
  })
  const clockRef = useRef(clock)
  clockRef.current = clock
  const mounted = useRef(false)

  // One map for the life of the page.
  useEffect(() => {
    registerTerrain()
    const state = live.current
    const first = state.track
    const heading = headingAt(first, 0, 0, 220) ?? 0
    state.bearing = heading
    const motionless = reducedMotion.matches
    const map = new MapLibre({
      container: box.current!,
      style: buildStyle({ track: first, labels: state.labels, terrain: !state.lite }),
      center: [first.lon[0], first.lat[0]],
      zoom: chaseZoom(first),
      pitch: PITCH,
      bearing: heading,
      maxPitch: 72,
      pixelRatio: Math.min(window.devicePixelRatio || 1, 2),
      fadeDuration: 0,
      attributionControl: { compact: window.innerWidth < 900 },
      canvasContextAttributes: { antialias: true },
    })
    mapRef.current = map
    // The track draws over the map and under the marker.
    const overlay = new TrackOverlay()
    overlay.readTheme()
    overlay.setTrack(first, state.colorBy)
    map.getCanvasContainer().insertBefore(overlay.canvas, map.getCanvas().nextSibling)
    const paint = () => {
      const s = live.current
      overlay.draw(map, s.head, s.head - cometLength(s.track), true)
    }
    map.on("render", paint)
    if (motionless) {
      map.fitBounds(first.bbox, { padding: OVERVIEW, pitch: 55, bearing: -18, duration: 0 })
    }

    const dot = document.createElement("div")
    dot.className = "replay-marker"
    dot.innerHTML = '<span class="replay-marker__halo"></span><span class="replay-marker__core"></span>'
    markerRef.current = new Marker({ element: dot, pitchAlignment: "viewport", rotationAlignment: "viewport", opacityWhenCovered: "0.35" })
      .setLngLat([first.lon[0], first.lat[0]])
      .addTo(map)

    const stopUser = (event: { originalEvent?: Event }) => {
      if (event.originalEvent) onUserMoveRef.current()
    }
    map.on("dragstart", stopUser)
    map.on("rotatestart", stopUser)
    map.on("pitchstart", stopUser)
    map.on("zoomstart", stopUser)
    // A tile that cannot load is drawn from its parent; nothing for the console.
    map.on("error", () => undefined)
    // The marker sits a little below the middle on a wide map, and a little above it on a phone,
    // where the title and the live numbers cover the bottom of the map.
    const pad = () => {
      overlay.resize(box.current?.clientWidth ?? 0, box.current?.clientHeight ?? 0)
      const h = box.current?.clientHeight ?? 0
      const narrow = (box.current?.clientWidth ?? 0) < 640
      live.current.wide = !narrow
      map.setPadding(narrow ? { top: 0, bottom: Math.round(h * 0.3), left: 0, right: 0 } : { top: Math.round(h * 0.22), bottom: 0, left: 0, right: 0 })
    }
    // On a wide map the whole track stays in the open ground between the top bar and the live numbers.
    const section = box.current!.closest("section")
    const header = section?.querySelector("header") ?? null
    const hud = section?.querySelector("[data-map-hud]") ?? null
    const clear: Clear = { top: 0, bottom: 0, left: 0, right: 0 }
    const measure = () => {
      const el = box.current
      if (!el) return
      const r = el.getBoundingClientRect()
      const room = 32
      const top = header?.getBoundingClientRect().bottom ?? r.top
      const bottom = hud?.getBoundingClientRect().top ?? r.bottom
      clear.top = top - r.top + room
      clear.bottom = bottom - r.top - room
      clear.left = room
      clear.right = r.width - room
    }
    pad()
    measure()
    const resize = new ResizeObserver(() => {
      map.resize()
      pad()
      measure()
    })
    resize.observe(box.current!)
    const remeasure = new ResizeObserver(measure)
    for (const el of [header, hud]) if (el) remeasure.observe(el)

    const restyle = () => {
      const s = live.current
      overlay.readTheme()
      overlay.setTrack(s.track, s.colorBy)
      map.setStyle(buildStyle({ track: s.track, labels: s.labels, terrain: !s.lite }), { diff: true })
      map.once("styledata", () => draw(clock.t, true))
    }
    const unscheme = onSchemeChange(restyle)
    restyleRef.current = restyle

    const draw = (t: number, jump = false) => {
      const s = live.current
      const tr = s.track
      const here = sampleAtTime(tr, t)
      markerRef.current?.setLngLat([here.lon, here.lat])
      s.head = here.d
      map.triggerRepaint()
      const now = performance.now()
      const dt = s.last ? Math.min(0.25, (now - s.last) / 1000) : 0.016
      s.last = now
      // A phone that misses its frames gets the lite map: flat terrain. Frames are judged thirty at a
      // time, after the first fifteen, which load tiles on every device.
      if (clock.playing && !jump && !s.lite && !s.slowSent) {
        s.frames.push(dt * 1000)
        if (s.frames.length >= 45) {
          const late = s.frames.slice(-30).filter((ms) => ms > 22).length
          if (late >= 5) {
            s.slowSent = true
            onSlowRef.current()
          }
          s.frames = s.frames.slice(-15)
        }
      }
      if (!s.follow || reducedMotion.matches) return
      const wanted = headingAt(tr, here.d, tr.sport === "ride" ? 120 : 40, tr.sport === "ride" ? 420 : 160)
      const leap = Math.abs(t - s.lastT) > 120
      s.lastT = t
      if (wanted != null) {
        const ease = jump || leap ? 1 : 1 - Math.exp(-dt * 1.6)
        s.bearing = (s.bearing + turn(s.bearing, wanted) * ease + 360) % 360
      }
      const base = chaseZoom(tr)
      const snap = jump || leap || !Number.isFinite(s.zoom)
      let zoom = snap || !s.wide ? base : s.zoom
      map.jumpTo({ center: [here.lon, here.lat], bearing: s.bearing, pitch: PITCH, zoom })
      if (s.wide) {
        // Out quickly when the track would run under the bars, back in slowly when there is room again. The camera
        // stays a chase camera: track left behind it may leave the view, but never by more than this much zoom.
        for (let k = 0; k < (snap ? 4 : 1); k++) {
          const want = Math.max(base - fitRange(tr), Math.min(base, zoom + fitZoom(map, tr, here, clear)))
          zoom = snap ? want : zoom + (want - zoom) * (1 - Math.exp(-dt * (want < zoom ? 8 : 0.8)))
          map.jumpTo({ zoom })
        }
      }
      s.zoom = zoom
    }
    drawRef.current = draw
    const unsubscribe = clock.subscribe((t) => draw(t))
    map.once("load", () => draw(clock.t, true))
    // On a small screen the credit line stays folded behind its (i) button until the person opens it.
    const credit = box.current!.querySelector<HTMLElement>(".maplibregl-ctrl-attrib")
    let opened = false
    const fold = new MutationObserver(() => {
      if (!opened && credit?.classList.contains("maplibregl-compact-show")) {
        credit.classList.remove("maplibregl-compact-show")
        credit.setAttribute("open", "")
      }
    })
    if (credit) {
      fold.observe(credit, { attributes: true, attributeFilter: ["class"] })
      credit.querySelector(".maplibregl-ctrl-attrib-button")?.addEventListener("pointerdown", () => (opened = true), { once: true })
    }

    return () => {
      unsubscribe()
      unscheme()
      fold.disconnect()
      resize.disconnect()
      remeasure.disconnect()
      markerRef.current?.remove()
      map.off("render", paint)
      overlay.canvas.remove()
      map.remove()
      mapRef.current = null
    }
    // The map is made once; later changes arrive through the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])


  // A new activity, a new coloring, or the lite switch restyles the map in place.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (!mounted.current) {
      mounted.current = true
      void prefetchRoute(track)
      return
    }
    live.current.lastT = -1e9
    restyleRef.current()
    void prefetchRoute(track)
    if (reducedMotion.matches) {
      map.fitBounds(track.bbox, { padding: OVERVIEW, pitch: 55, bearing: -18, duration: 0 })
    } else {
      live.current.bearing = headingAt(track, 0, 0, 220) ?? live.current.bearing
    }
  }, [track, colorBy, lite])

  // Following again snaps the camera back behind the marker.
  useEffect(() => {
    if (follow) drawRef.current(clockRef.current.t, true)
  }, [follow])

  return (
    <div className="absolute inset-0">
      <div ref={box} className="size-full touch-none" aria-label={`3D map of ${track.name}`} role="img" />
    </div>
  )
}
