import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { FilterBar } from "@/components/FilterBar"
import { GetDialog } from "@/components/GetDialog"
import { PaperHero } from "@/components/PaperHero"
import { PictureDialog } from "@/components/PictureDialog"
import { WishCard, type CardState } from "@/components/WishCard"
import { fill, readConfig, readCopy, type Item } from "@/lib/config"
import { inBand, moneyFormat, priceBands } from "@/lib/money"
import { reducedMotion, sleep, weakDevice } from "@/lib/motion"
import { loadSaved, save } from "@/lib/store"
import { cn } from "@/lib/utils"

type Point = { x: number; y: number }

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))

function mergeOrder(saved: string[], items: Item[]): string[] {
  const ids = items.map((item) => item.id)
  return [...saved.filter((id) => ids.includes(id)), ...ids.filter((id) => !saved.includes(id))]
}

function shuffled<T>(list: T[]): T[] {
  const out = [...list]
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  if (out.length > 2 && out.every((v, i) => v === list[i])) out.push(out.shift() as T)
  return out
}

export default function App() {
  const config = useMemo(readConfig, [])
  const copy = useMemo(() => readCopy(config), [config])
  const format = useMemo(() => moneyFormat(config.currency, config.items), [config])
  const whole = useMemo(() => moneyFormat(config.currency, []), [config])
  const bands = useMemo(() => priceBands(config.items), [config])
  const saved = useMemo(loadSaved, [])
  const still = useMemo(reducedMotion, [])
  const weak = useMemo(weakDevice, [])

  const [band, setBand] = useState(() => (saved && bands.some((b) => b.id === saved.band) ? saved.band : "all"))
  const [hideGotten, setHideGotten] = useState(saved?.hideGotten ?? false)
  const [order, setOrder] = useState(() => mergeOrder(saved?.order ?? [], config.items))
  const [promised, setPromised] = useState<string[]>(saved?.promised ?? [])
  const [turn, setTurn] = useState(0)
  const [getting, setGetting] = useState<Item | null>(null)
  const [picture, setPicture] = useState<{ item: Item; thumb: string | null } | null>(null)

  const keep = useRef(saved !== null)
  const latest = useRef({ band, hideGotten, order, promised })
  latest.current = { band, hideGotten, order, promised }
  useEffect(() => {
    if (keep.current) save({ band, hideGotten, order, promised })
  }, [band, hideGotten, order, promised])

  const byId = useMemo(() => new Map(config.items.map((item) => [item.id, item])), [config])
  const stateOf = useCallback(
    (item: Item): CardState => (item.claimed ? "gotten" : promised.includes(item.id) ? "yours" : "open"),
    [promised],
  )
  const current = bands.find((b) => b.id === band)
  const inView = order.map((id) => byId.get(id) as Item).filter((item) => inBand(item, current))
  const visible = inView.filter((item) => !hideGotten || stateOf(item) === "open")
  const openItems = inView.filter((item) => stateOf(item) === "open")
  const total = openItems.reduce((sum, item) => sum + item.price, 0)
  const visibleKey = visible.map((item) => item.id).join(" ")

  // Elements by item id: the slot that deals and moves, and the layer the pointer tilts.
  const slots = useRef(new Map<string, HTMLDivElement>())
  const tilts = useRef(new Map<string, HTMLDivElement>())
  const refFns = useRef(new Map<string, [(el: HTMLDivElement | null) => void, (el: HTMLDivElement | null) => void]>())
  const refsFor = (id: string) => {
    let fns = refFns.current.get(id)
    if (!fns) {
      fns = [
        (el) => (el ? slots.current.set(id, el) : slots.current.delete(id)),
        (el) => (el ? tilts.current.set(id, el) : tilts.current.delete(id)),
      ]
      refFns.current.set(id, fns)
    }
    return fns
  }
  const hero = useRef<HTMLDivElement>(null)
  const grid = useRef<HTMLDivElement>(null)

  const firstMount = useRef(true)
  const flipFrom = useRef<Map<string, DOMRect> | null>(null)
  const dealFan = useRef<Map<string, number> | null>(null)
  const busy = useRef(false)

  const deckPoint = (fromHero: boolean): Point => {
    const h = hero.current?.getBoundingClientRect()
    if (fromHero && h && h.bottom > 120) return { x: window.innerWidth / 2, y: h.bottom - 80 }
    const top = grid.current?.getBoundingClientRect().top ?? 0
    return { x: window.innerWidth / 2, y: clamp(top + 220, 160, window.innerHeight * 0.55) }
  }

  const onScreen = (r: DOMRect) => r.bottom > -40 && r.top < window.innerHeight + 40

  /** Deals the visible cards out from a point, one after another. */
  const deal = (ids: string[], from: Point, fan: Map<string, number> | null, first: boolean) => {
    let n = 0
    ids.forEach((id) => {
      const el = slots.current.get(id)
      if (!el) return
      el.getAnimations().forEach((a) => a.cancel())
      const r = el.getBoundingClientRect()
      if (!onScreen(r) && !fan?.has(id)) return
      const dx = from.x - (r.left + r.width / 2)
      const dy = from.y - (r.top + r.height / 2)
      const rot = fan?.get(id) ?? (n % 2 ? 1 : -1) * (6 + ((n * 7) % 9))
      el.style.transformOrigin = "50% 85%"
      el.animate(
        [
          { transform: `translate(${dx}px, ${dy}px) rotate(${rot}deg) scale(${first ? 0.4 : 0.62})`, opacity: first ? 0 : 1 },
          { opacity: 1, offset: 0.25 },
          { transform: "none", opacity: 1 },
        ],
        { duration: first ? 820 : 720, delay: n * (first ? 60 : 48), easing: "cubic-bezier(0.2, 0.8, 0.25, 1)", fill: "backwards" },
      )
      n += 1
    })
  }

  useLayoutEffect(() => {
    const ids = visibleKey ? visibleKey.split(" ") : []
    if (firstMount.current) {
      firstMount.current = false
      if (!still) deal(ids, deckPoint(true), null, true)
      return
    }
    const fan = dealFan.current
    const snap = flipFrom.current
    dealFan.current = null
    flipFrom.current = null
    if (still) return
    if (fan) {
      deal(ids, deckPoint(false), fan, false)
      return
    }
    if (!snap) return
    ids.forEach((id, i) => {
      const el = slots.current.get(id)
      if (!el) return
      el.getAnimations().forEach((a) => a.cancel())
      const r = el.getBoundingClientRect()
      const old = snap.get(id)
      if (old) {
        const dx = old.left - r.left
        const dy = old.top - r.top
        if (Math.abs(dx) + Math.abs(dy) > 1)
          el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], {
            duration: 600,
            easing: "cubic-bezier(0.22, 1, 0.36, 1)",
          })
      } else if (onScreen(r)) {
        el.animate(
          [{ transform: "translateY(28px) scale(0.9)", opacity: 0 }, { transform: "none", opacity: 1 }],
          { duration: 520, delay: 140 + i * 35, easing: "cubic-bezier(0.22, 1, 0.36, 1)", fill: "backwards" },
        )
      }
    })
    // visibleKey is the whole input; the helpers read refs only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleKey])

  /** A change of filter: the cards that stay glide to their new places and every price rolls a lap. */
  const changeView = (change: () => void) => {
    const snap = new Map<string, DOMRect>()
    slots.current.forEach((el, id) => snap.set(id, el.getBoundingClientRect()))
    flipFrom.current = snap
    setTurn((t) => t + 1)
    change()
  }

  /** Shuffle: the cards gather into a fanned hand, then deal out in a new order. */
  const shuffle = async () => {
    if (busy.current) return
    const ids = visibleKey ? visibleKey.split(" ") : []
    const next = shuffled(latest.current.order)
    if (still || ids.length < 2) {
      setOrder(next)
      return
    }
    busy.current = true
    const at = deckPoint(false)
    const fan = new Map<string, number>()
    const live = ids.filter((id) => {
      const el = slots.current.get(id)
      return el && onScreen(el.getBoundingClientRect())
    })
    const spread = Math.min(9, 64 / Math.max(1, live.length))
    const moves = live.map((id, i) => {
      const el = slots.current.get(id) as HTMLDivElement
      el.getAnimations().forEach((a) => a.cancel())
      const r = el.getBoundingClientRect()
      const rot = (i - (live.length - 1) / 2) * spread
      fan.set(id, rot)
      el.style.transformOrigin = "50% 85%"
      return el.animate(
        [
          { transform: "none" },
          { transform: `translate(${at.x - (r.left + r.width / 2)}px, ${at.y - (r.top + r.height / 2)}px) rotate(${rot}deg) scale(0.62)` },
        ],
        { duration: 520, delay: i * 30, easing: "cubic-bezier(0.65, 0, 0.35, 1)", fill: "forwards" },
      ).finished
    })
    await Promise.allSettled(moves)
    await sleep(220)
    dealFan.current = fan
    setOrder(next)
    busy.current = false
  }

  const userShuffle = () => {
    keep.current = true
    void shuffle()
  }
  const userBand = (id: string) => {
    keep.current = true
    if (id !== latest.current.band) changeView(() => setBand(id))
  }
  const userHide = (on: boolean) => {
    keep.current = true
    changeView(() => setHideGotten(on))
  }
  const onGet = useCallback((item: Item) => setGetting(item), [])
  const onUndo = useCallback((item: Item) => {
    keep.current = true
    setPromised((list) => list.filter((id) => id !== item.id))
  }, [])
  const onSent = (item: Item) => {
    keep.current = true
    setPromised((list) => (list.includes(item.id) ? list : [...list, item.id]))
    window.setTimeout(() => setGetting(null), 160)
  }
  const onPicture = useCallback((item: Item, thumb: string | null) => item.image && setPicture({ item, thumb }), [])

  // The first visit plays the page once by itself: a filter, back to everything, and a shuffle. Any touch, key, or
  // wheel hands it over, with every card showing.
  useEffect(() => {
    if (saved || still) return
    const mid = bands[Math.floor(bands.length / 2)]?.id
    let over = false
    const timers: number[] = []
    const at = (ms: number, fn: () => void) => timers.push(window.setTimeout(() => !over && fn(), ms))
    const end = () => {
      over = true
      timers.forEach(clearTimeout)
      events.forEach((e) => window.removeEventListener(e, takeOver))
    }
    const takeOver = () => {
      if (over) return
      end()
      if (latest.current.band !== "all") changeView(() => setBand("all"))
    }
    const events = ["pointerdown", "keydown", "wheel", "touchstart"]
    events.forEach((e) => window.addEventListener(e, takeOver, { passive: true }))
    if (mid) {
      at(3300, () => changeView(() => setBand(mid)))
      at(5300, () => changeView(() => setBand("all")))
    }
    at(6300, () => void shuffle())
    at(9600, () => {
      end()
      keep.current = true
      save(latest.current)
    })
    return end
    // The visit plays once, on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // One frame loop moves the hero's layers by depth and tilts each card toward the pointer, the phone's tilt, or, for
  // the first twelve seconds, a slow drifting point.
  useEffect(() => {
    if (still) return
    const begin = performance.now()
    // Only a mouse steers the cards, by the pointer or the drifting point; a phone's cards rest flat and lean a few degrees as it moves.
    const fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches
    let pointer: Point | null = null
    let tilt: Point | null = null
    let heroOn = true
    const shown = new Set<string>()
    const pose = new Map<string, { rx: number; ry: number; z: number }>()
    const parts = new Map<HTMLElement, { band: HTMLElement | null; glare: HTMLElement | null }>()
    const layers = Array.from(hero.current?.querySelectorAll<HTMLElement>(".hero-layer") ?? []).map((layer) => ({
      svg: layer.firstElementChild as HTMLElement,
      depth: Number(layer.dataset.depth),
    }))

    const seen = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        const id = (e.target as HTMLElement).dataset.id
        if (id) e.isIntersecting ? shown.add(id) : shown.delete(id)
      })
    }, { rootMargin: "80px" })
    const watchSlots = () => slots.current.forEach((el) => seen.observe(el))
    watchSlots()
    const heroSeen = new IntersectionObserver(([e]) => (heroOn = e.isIntersecting))
    if (hero.current) heroSeen.observe(hero.current)
    const recheck = window.setInterval(watchSlots, 1000)

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "touch") pointer = { x: e.clientX, y: e.clientY }
    }
    const onLeave = () => (pointer = null)
    // The phone's first reading is its rest: the cards lean only as it moves from there, and a few degrees of hand
    // shake leave them flat.
    let rest: { gamma: number; beta: number } | null = null
    const lean = (d: number) => (Math.abs(d) < 2 ? 0 : clamp(d / 28, -1, 1))
    const onOrient = (e: DeviceOrientationEvent) => {
      if (e.gamma == null || e.beta == null) return
      rest ??= { gamma: e.gamma, beta: e.beta }
      tilt = { x: lean(e.gamma - rest.gamma), y: lean(e.beta - rest.beta) }
    }
    type Asking = typeof DeviceOrientationEvent & { requestPermission?: () => Promise<string> }
    const ask = () => {
      const D = window.DeviceOrientationEvent as Asking | undefined
      D?.requestPermission?.().then((r) => r === "granted" && window.addEventListener("deviceorientation", onOrient)).catch(() => {})
    }
    window.addEventListener("pointermove", onMove, { passive: true })
    document.documentElement.addEventListener("mouseleave", onLeave)
    window.addEventListener("deviceorientation", onOrient)
    window.addEventListener("pointerdown", ask, { once: true })

    let frame = 0
    const step = (now: number) => {
      const t = (now - begin) / 1000
      const W = window.innerWidth
      const H = window.innerHeight
      const drift = !pointer && !tilt && t < 12 ? { x: W * (0.5 + 0.42 * Math.sin(t * 0.8 - 0.4)), y: H * (0.6 + 0.3 * Math.sin(t * 1.3 + 0.8)) } : null
      const scene = pointer ?? drift
      const p = fine ? (pointer ?? drift) : null

      if (heroOn) {
        const nx = scene ? (scene.x / W) * 2 - 1 : (tilt?.x ?? 0)
        const ny = scene ? (scene.y / H) * 2 - 1 : (tilt?.y ?? 0)
        for (const { svg, depth } of layers) {
          const x = -(nx + Math.sin(t * 0.45) * 0.3) * depth * 38
          const y = -ny * depth * 12 + Math.sin(t * 0.7 + depth * 4) * depth * 5
          svg.style.transform = `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0)`
        }
      }

      tilts.current.forEach((el, id) => {
        if (!shown.has(id)) return
        const slot = slots.current.get(id)
        if (!slot) return
        const r = slot.getBoundingClientRect()
        let rx = 0
        let ry = 0
        let z = 0
        if (p) {
          const ux = (p.x - (r.left + r.width / 2)) / (r.width / 2)
          const uy = (p.y - (r.top + r.height / 2)) / (r.height / 2)
          const d = Math.hypot(ux, uy)
          const k = d <= 1.1 ? 1 : Math.max(0.22, 1.1 / d)
          ry = clamp(ux, -1, 1) * 13 * k
          rx = -clamp(uy, -1, 1) * 10 * k
          z = d <= 1 ? 1 : 0
        } else if (tilt) {
          ry = tilt.x * 4
          rx = -tilt.y * 3
        }
        const c = pose.get(id) ?? { rx: 0, ry: 0, z: 0 }
        if (Math.abs(c.rx - rx) + Math.abs(c.ry - ry) + Math.abs(c.z - z) < 0.01 && pose.has(id)) return
        const ease = fine ? 0.1 : 0.06
        c.rx += (rx - c.rx) * ease
        c.ry += (ry - c.ry) * ease
        c.z += (z - c.z) * 0.12
        pose.set(id, c)
        // At rest the card has no transform and no layer of its own, so its text draws at full sharpness.
        if (!rx && !ry && !z && Math.abs(c.rx) + Math.abs(c.ry) + Math.abs(c.z) < 0.02) {
          c.rx = c.ry = c.z = 0
          el.style.transform = ""
          el.style.willChange = ""
          return
        }
        el.style.willChange = "transform"
        el.style.transform = `perspective(1100px) rotateX(${c.rx.toFixed(2)}deg) rotateY(${c.ry.toFixed(2)}deg) translateZ(${(c.z * 18).toFixed(1)}px)`
        let part = parts.get(el)
        if (!part) {
          part = { band: el.querySelector(".sheen-band"), glare: el.querySelector(".glare") }
          parts.set(el, part)
        }
        const sx = 0.5 + c.ry / 26
        const sy = 0.5 - c.rx / 20
        if (part.band) part.band.style.transform = `translateX(${(sx * 1.7 * r.width).toFixed(1)}px) skewX(-14deg)`
        if (part.glare) part.glare.style.transform = `translate(${(sx * r.width).toFixed(1)}px, ${(sy * r.height).toFixed(1)}px)`
      })
      frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => {
      cancelAnimationFrame(frame)
      window.clearInterval(recheck)
      seen.disconnect()
      heroSeen.disconnect()
      window.removeEventListener("pointermove", onMove)
      document.documentElement.removeEventListener("mouseleave", onLeave)
      window.removeEventListener("deviceorientation", onOrient)
      window.removeEventListener("pointerdown", ask)
    }
  }, [still])

  const firstFold = useRef(new Map<string, number>())
  const foldDelay = (id: string, index: number) => {
    let d = firstFold.current.get(id)
    if (d === undefined) {
      d = firstMount.current ? 620 + index * 60 : 60
      firstFold.current.set(id, d)
    }
    return d
  }

  const owner = config.owner.name
  return (
    <div className={cn("min-h-dvh", weak && "no-sheen")}>
      <PaperHero
        ref={hero}
        eyebrow={fill(copy.eyebrow, { owner })}
        title={config.occasion}
        line={fill(copy.tagline, { owner })}
      />
      <FilterBar
        copy={copy}
        total={total}
        open={openItems.length}
        count={inView.length}
        format={format}
        whole={whole}
        bands={bands}
        band={band}
        hideGotten={hideGotten}
        onBand={userBand}
        onHideGotten={userHide}
        onShuffle={userShuffle}
      />
      <main className="pad-safe-bottom mx-auto w-full max-w-[1600px] px-4 pt-5 sm:px-6 lg:px-10 lg:pt-7">
        <div ref={grid} className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 lg:gap-7 xl:grid-cols-4">
          {visible.map((item, i) => {
            const [slotRef, tiltRef] = refsFor(item.id)
            return (
              <WishCard
                key={item.id}
                item={item}
                state={stateOf(item)}
                format={format}
                turn={turn}
                copy={copy}
                owner={owner}
                foldDelay={foldDelay(item.id, i)}
                slotRef={slotRef}
                tiltRef={tiltRef}
                onGet={onGet}
                onUndo={onUndo}
                onPicture={onPicture}
              />
            )
          })}
        </div>
        {visible.length === 0 && (
          <div className="flex flex-col items-center gap-4 py-24 text-center">
            <p className="display text-[1.4rem] font-semibold">{copy.empty}</p>
            <Button variant="outline" className="rounded-full" onClick={() => { userBand("all"); if (hideGotten) userHide(false) }}>
              {copy.showAll}
            </Button>
          </div>
        )}
      </main>
      <GetDialog
        item={getting}
        owner={config.owner}
        copy={copy}
        priceText={getting ? format.format(getting.price) : ""}
        onClose={() => setGetting(null)}
        onSent={onSent}
      />
      <PictureDialog
        item={picture?.item ?? null}
        thumb={picture?.thumb ?? null}
        priceText={picture ? format.format(picture.item.price) : ""}
        onClose={() => setPicture(null)}
      />
    </div>
  )
}
