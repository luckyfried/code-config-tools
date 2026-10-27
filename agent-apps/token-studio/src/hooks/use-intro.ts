import { useEffect, useRef, useState } from "react"
import type { Settings } from "@/lib/tokens"
import { prefersReducedMotion } from "./use-media"

type Controls = {
  enabled: boolean
  seed: Settings
  setSettings: (update: (s: Settings) => Settings) => void
  setTab: (tab: string) => void
  flip: () => void
}

const easeInOut = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2)
const clamp01 = (t: number) => Math.min(1, Math.max(0, t))

/** The ratio the tour steps to and back from: a step up the scale, or down when the seed is already large. */
const tourRatio = (seed: number) => (seed < 1.3 ? 1.333 : 1.2)
/** The spacing unit the tour opens up to alongside the scale, or closes down to when the seed is already wide. */
const tourSpace = (seed: number) => (seed < 6 ? seed + 2 : seed - 2)

/**
 * The first visit's tour, once: the hue runs a full turn of the wheel and lands back on the brand, the type scale and
 * the spacing step out and back so the paragraphs and the poster ease, and the poster turns to its other surface and
 * home again. Any touch, click, or key hands the page to the person at once, with the seed's values put back.
 */
export function useIntro({ enabled, seed, setSettings, setTab, flip }: Controls) {
  const [running, setRunning] = useState(() => enabled && !prefersReducedMotion())
  const live = useRef({ setSettings, setTab, flip })
  live.current = { setSettings, setTab, flip }

  useEffect(() => {
    if (!running) return
    const { hue } = seed.brand
    const ratio = seed.typeScaleRatio
    const peak = tourRatio(ratio)
    const space = seed.spacingBase
    const roomy = tourSpace(space)
    const fired = new Set<string>()
    let flipped = 0
    let frame = 0
    let last = ""
    const start = performance.now()

    const once = (key: string, at: number, now: number, act: () => void) => {
      if (now >= at && !fired.has(key)) {
        fired.add(key)
        act()
      }
    }
    const tick = (time: number) => {
      const t = time - start
      const { setSettings, setTab, flip } = live.current
      const turn = easeInOut(clamp01((t - 120) / 1030))
      const nextHue = (hue + 360 * turn) % 360
      // The scale and the spacing step once out and once back; the paragraphs and the poster ease to each step in CSS.
      const stepped = t >= 3500 && t < 5000
      const nextRatio = stepped ? peak : ratio
      const nextSpace = stepped ? roomy : space
      const key = `${nextHue.toFixed(2)} ${nextRatio} ${nextSpace}`
      if (key !== last) {
        last = key
        setSettings((s) => ({ ...s, brand: { ...s.brand, hue: nextHue }, typeScaleRatio: nextRatio, spacingBase: nextSpace }))
      }
      once("type", 3100, t, () => setTab("type"))
      once("flip", 6000, t, () => (flip(), flipped++))
      once("back", 7800, t, () => (flip(), flipped--))
      once("color", 8600, t, () => setTab("color"))
      if (t < 8600) frame = requestAnimationFrame(tick)
      else finish()
    }
    const finish = () => {
      cancelAnimationFrame(frame)
      window.removeEventListener("pointerdown", stop, true)
      window.removeEventListener("keydown", stop, true)
      window.removeEventListener("wheel", stop, true)
      live.current.setSettings((s) => ({ ...s, brand: { ...s.brand, hue }, typeScaleRatio: ratio, spacingBase: space }))
      setRunning(false)
    }
    const stop = () => {
      if (flipped) live.current.flip()
      flipped = 0
      finish()
    }
    window.addEventListener("pointerdown", stop, true)
    window.addEventListener("keydown", stop, true)
    window.addEventListener("wheel", stop, { capture: true, passive: true })
    frame = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener("pointerdown", stop, true)
      window.removeEventListener("keydown", stop, true)
      window.removeEventListener("wheel", stop, true)
    }
  }, [running, seed])

  return running
}
