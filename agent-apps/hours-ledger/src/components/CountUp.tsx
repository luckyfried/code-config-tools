import { useEffect, useRef, useState } from "react"

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches

// A figure that counts up from zero the first time it shows, in step with the bars and the strip filling; after that it follows the value.
export function CountUp({ value, suffix = "", delay = 320, duration = 1000 }: { value: number; suffix?: string; delay?: number; duration?: number }) {
  const [shown, setShown] = useState(() => (reduced() ? value : 0))
  const done = useRef(reduced())
  const target = useRef(value)
  target.current = value

  useEffect(() => {
    if (done.current) return
    let raf = 0
    const t0 = performance.now() + delay
    const step = (t: number) => {
      const p = Math.min(1, Math.max(0, (t - t0) / duration))
      setShown(target.current * (1 - Math.pow(1 - p, 3)))
      if (p < 1) raf = requestAnimationFrame(step)
      else done.current = true
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [delay, duration])

  return <span className="tnum">{(done.current ? value : shown).toFixed(1) + suffix}</span>
}
