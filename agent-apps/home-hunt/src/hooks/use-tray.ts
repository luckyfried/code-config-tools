import { useCallback, useEffect, useState } from "react"

const STORE = "home-hunt"
export const TRAY_MAX = 3

function readHash(): string[] | null {
  const m = /(?:^#|&)compare=([^&]*)/.exec(window.location.hash)
  if (!m) return null
  return decodeURIComponent(m[1]).split(",").map((s) => s.trim()).filter(Boolean).slice(0, TRAY_MAX)
}

function readStore(): string[] | null {
  try {
    const v = JSON.parse(localStorage.getItem(STORE) ?? "null") as { tray?: unknown } | null
    return Array.isArray(v?.tray) ? v.tray.filter((x): x is string => typeof x === "string").slice(0, TRAY_MAX) : null
  } catch {
    return null
  }
}

function writeStore(tray: string[]) {
  try {
    localStorage.setItem(STORE, JSON.stringify({ tray }))
  } catch {
    // A browser that keeps nothing still compares; the tray just starts empty next time.
  }
}

// The compare tray: up to three homes, kept on this machine; compare itself lives in the address, #compare=<id>,<id>.
export function useTray(starter: string[]) {
  const [tray, setTray] = useState<string[]>(() => readHash() ?? readStore() ?? starter)
  const [open, setOpen] = useState<boolean>(() => (readHash()?.length ?? 0) >= 2)

  useEffect(() => {
    const onHash = () => {
      const ids = readHash()
      if (ids && ids.length >= 2) {
        setTray(ids)
        setOpen(true)
      } else setOpen(false)
    }
    window.addEventListener("hashchange", onHash)
    return () => window.removeEventListener("hashchange", onHash)
  }, [])

  const save = useCallback((next: string[], keep = true) => {
    setTray(next)
    if (keep) writeStore(next)
  }, [])

  const add = useCallback(
    (id: string, keep = true) => {
      setTray((t) => {
        if (t.includes(id)) return t
        const next = [...t, id].slice(-TRAY_MAX)
        if (keep) writeStore(next)
        return next
      })
    },
    [],
  )

  const remove = useCallback((id: string) => {
    setTray((t) => {
      const next = t.filter((x) => x !== id)
      writeStore(next)
      if (next.length < 2) {
        setOpen(false)
        if (readHash()) history.replaceState(null, "", window.location.pathname + window.location.search)
      } else if (readHash()) history.replaceState(null, "", `#compare=${next.join(",")}`)
      return next
    })
  }, [])

  const toggle = useCallback((id: string) => (tray.includes(id) ? remove(id) : add(id)), [tray, add, remove])

  const show = useCallback(
    (ids: string[], keepAddress = true) => {
      if (ids.length < 2) return
      setOpen(true)
      if (keepAddress) history.replaceState(null, "", `#compare=${ids.join(",")}`)
    },
    [],
  )

  const hide = useCallback(() => {
    setOpen(false)
    if (readHash()) history.replaceState(null, "", window.location.pathname + window.location.search)
  }, [])

  return { tray, open, add, remove, toggle, show, hide, save }
}
