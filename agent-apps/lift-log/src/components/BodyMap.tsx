import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"
import { MUSCLE_LABEL, type Muscle } from "@/lib/config"
import { fmtSets, type MuscleWeek } from "@/lib/lift"

/** The order regions take their shade on load: shoulders down to calves, front and back together. */
const TINT_ORDER: Muscle[] = [
  "traps",
  "shoulders",
  "chest",
  "biceps",
  "triceps",
  "lats",
  "forearms",
  "abs",
  "obliques",
  "lower-back",
  "glutes",
  "quads",
  "hamstrings",
  "calves",
]
/** On the page's opening the map shows untinted for a beat, then each region fades in, 90 ms after the one before; a map opened later starts at once. */
const TINT_START_MS = 650
const TINT_RUN_MS = TINT_ORDER.length * 90 + 650
let opened = false

let drawing: Promise<string> | null = null
const loadDrawing = () =>
  (drawing ??= fetch("./body.svg").then((r) => (r.ok ? r.text() : Promise.reject(new Error(String(r.status))))))

type Props = {
  week: MuscleWeek[]
  focus?: Muscle | null
  onPick?: (m: Muscle) => void
  flash?: { key: string; muscles: Muscle[] } | null
  className?: string
}

export function BodyMap({ week, focus = null, onPick, flash, className }: Props) {
  const host = useRef<HTMLDivElement>(null)
  const [ready, setReady] = useState(false)
  const [tinted, setTinted] = useState(false)
  const [settled, setSettled] = useState(false)

  useEffect(() => {
    let alive = true
    loadDrawing()
      .then((text) => {
        const el = host.current
        if (!alive || !el) return
        el.innerHTML = text
        el.querySelectorAll<SVGPathElement>("path[data-muscle]").forEach((p) => {
          p.style.setProperty("--i", String(TINT_ORDER.indexOf(p.dataset.muscle as Muscle)))
        })
        setReady(true)
      })
      .catch(() => {
        drawing = null
      })
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (!ready) return
    const calm = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const wait = calm || opened ? 50 : TINT_START_MS
    opened = true
    const start = window.setTimeout(() => setTinted(true), wait)
    const done = window.setTimeout(() => setSettled(true), wait + (calm ? 250 : TINT_RUN_MS))
    return () => {
      clearTimeout(start)
      clearTimeout(done)
    }
  }, [ready])

  useEffect(() => {
    const el = host.current
    if (!ready || !el) return
    const byMuscle = new Map(week.map((w) => [w.muscle, w]))
    el.querySelectorAll<SVGPathElement>("path[data-muscle]").forEach((p) => {
      const m = p.dataset.muscle as Muscle
      const w = byMuscle.get(m)
      p.dataset.level = String(w?.level ?? 0)
      const sets = w ? fmtSets(w.sets) : "0"
      p.setAttribute("aria-label", `${MUSCLE_LABEL[m]}, ${sets} ${sets === "1" ? "set" : "sets"} this week`)
      if (onPick) {
        p.setAttribute("role", "button")
        p.setAttribute("tabindex", "0")
      } else {
        p.removeAttribute("role")
        p.removeAttribute("tabindex")
      }
      if (focus === m) p.dataset.focus = ""
      else delete p.dataset.focus
    })
  }, [ready, week, focus, onPick])

  useEffect(() => {
    const el = host.current
    if (!ready || !el || !flash) return
    const paths = flash.muscles
      .map((m) => el.querySelector<SVGPathElement>(`path[data-muscle="${m}"]`))
      .filter((p): p is SVGPathElement => p !== null)
    paths.forEach((p) => p.removeAttribute("data-flash"))
    void el.offsetWidth
    paths.forEach((p) => p.setAttribute("data-flash", ""))
    const t = window.setTimeout(() => paths.forEach((p) => p.removeAttribute("data-flash")), 950)
    return () => clearTimeout(t)
  }, [ready, flash])

  const pickFrom = (target: EventTarget | null) => {
    const p = (target as Element | null)?.closest?.("path[data-muscle]") as SVGPathElement | null
    if (p && onPick) onPick(p.dataset.muscle as Muscle)
  }

  return (
    <div
      ref={host}
      className={cn(
        "body-map aspect-[436/444]",
        tinted && "is-tinted",
        settled && "is-settled",
        onPick && "is-interactive",
        focus && "has-focus",
        className,
      )}
      onClick={(e) => pickFrom(e.target)}
      onKeyDown={(e) => {
        if (e.key !== "Enter" && e.key !== " ") return
        if (!(e.target as Element).matches?.("path[data-muscle]")) return
        e.preventDefault()
        e.stopPropagation()
        pickFrom(e.target)
      }}
    />
  )
}
