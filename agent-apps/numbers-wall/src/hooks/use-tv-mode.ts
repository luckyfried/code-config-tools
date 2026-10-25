import { useCallback, useEffect, useRef, useState } from "react"
import { flushSync } from "react-dom"

const HASH = "#tv"
/** A wall left alone after it opens goes to TV mode after this long; once someone has used it, after half a minute. */
const IDLE_FIRST_MS = 4000
const IDLE_MS = 30000
const SETTLE_MS = 1000
const WALL_SCREEN = "(pointer: fine) and (min-width: 1024px)"
const ACTIVITY = ["pointermove", "pointerdown", "keydown", "wheel", "touchstart"] as const

function dialogOpen() {
  return document.querySelector('[role="dialog"]') !== null
}

/** Runs a change of view as a view transition where the browser has one, so each tile moves to its new place. */
function transition(update: () => void) {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches
  if (!document.startViewTransition || reduce) return update()
  document.startViewTransition(() => flushSync(update))
}

/**
 * TV mode drops everything but the tiles. F toggles it, Escape leaves it, and the address #tv opens the wall in it,
 * which is how a wall screen with no keyboard starts there. Entering from a key or a tap also asks for full screen.
 * On a desktop-sized screen a wall nobody touches goes to TV mode by itself, and the first move of the mouse or a key
 * brings the wall back.
 */
export function useTvMode() {
  const [tv, setTv] = useState(() => window.location.hash === HASH)
  const [byIdle, setByIdle] = useState(false)
  /** True once the view has changed between the wall and TV mode; the roll-up plays only on the first view. */
  const [moved, setMoved] = useState(false)
  const used = useRef(false)

  const change = useCallback((next: boolean, idle = false) => {
    transition(() => {
      setTv(next)
      setByIdle(next && idle)
      setMoved(true)
    })
    if (idle) return
    const url = new URL(window.location.href)
    url.hash = next ? HASH : ""
    window.history.replaceState(null, "", url.hash ? url : url.pathname + url.search)
    if (next && !document.fullscreenElement) {
      document.documentElement.requestFullscreen?.().catch(() => undefined)
    } else if (!next && document.fullscreenElement) {
      document.exitFullscreen().catch(() => undefined)
    }
  }, [])

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey || dialogOpen()) return
      const target = event.target as HTMLElement | null
      if (target?.closest("input, textarea, [contenteditable]")) return
      if (event.key === "f" || event.key === "F") {
        event.preventDefault()
        change(!tv)
      } else if (event.key === "Escape" && tv) {
        change(false)
      }
    }
    const onFullscreen = () => {
      if (!document.fullscreenElement && tv && !byIdle) change(false)
    }
    window.addEventListener("keydown", onKey)
    document.addEventListener("fullscreenchange", onFullscreen)
    return () => {
      window.removeEventListener("keydown", onKey)
      document.removeEventListener("fullscreenchange", onFullscreen)
    }
  }, [tv, byIdle, change])

  useEffect(() => {
    const screen = window.matchMedia(WALL_SCREEN)
    if (!screen.matches || (tv && !byIdle)) return
    let timer = 0
    const arm = () => {
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        if (!dialogOpen()) change(true, true)
        else arm()
      }, used.current ? IDLE_MS : IDLE_FIRST_MS)
    }
    const since = performance.now()
    const onActivity = (event: Event) => {
      // A pointer that did not move, or an event while the tiles are still moving into place, is the page settling.
      if (event instanceof PointerEvent && event.type === "pointermove" && !event.movementX && !event.movementY) return
      if (tv && performance.now() - since < SETTLE_MS) return
      used.current = true
      if (tv && byIdle) {
        const key = event instanceof KeyboardEvent ? event.key : ""
        if (key === "f" || key === "F" || key === "Escape") return
        change(false, true)
        return
      }
      arm()
    }
    if (!tv) arm()
    for (const type of ACTIVITY) window.addEventListener(type, onActivity, { passive: true })
    return () => {
      window.clearTimeout(timer)
      for (const type of ACTIVITY) window.removeEventListener(type, onActivity)
    }
  }, [tv, byIdle, change])

  useEffect(() => {
    const root = document.documentElement
    if (tv) root.dataset.tv = "on"
    else delete root.dataset.tv
  }, [tv])

  return [tv, change, moved] as const
}
