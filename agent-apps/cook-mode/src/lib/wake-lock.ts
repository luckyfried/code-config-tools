import { useEffect } from "react"

/** Keeps the screen on while cook mode is open, where the browser offers a wake lock. */
export function useWakeLock(active: boolean) {
  useEffect(() => {
    if (!active || !("wakeLock" in navigator)) return
    let lock: WakeLockSentinel | null = null
    let cancelled = false
    const request = async () => {
      try {
        lock = await navigator.wakeLock.request("screen")
        if (cancelled) void lock.release()
      } catch {
        lock = null
      }
    }
    const again = () => {
      if (document.visibilityState === "visible") void request()
    }
    void request()
    document.addEventListener("visibilitychange", again)
    return () => {
      cancelled = true
      document.removeEventListener("visibilitychange", again)
      void lock?.release()
    }
  }, [active])
}
