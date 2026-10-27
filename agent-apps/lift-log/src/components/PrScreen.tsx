import { useState, type CSSProperties } from "react"
import { useLog } from "@/lib/log-context"

/** A record sweeps gold across the whole screen, once, as the set lands, and the layer leaves when its glow has faded. */
export function PrScreen() {
  const { moment } = useLog()
  const [doneKey, setDoneKey] = useState<string | null>(null)
  if (!moment || doneKey === moment.key) return null
  return (
    <div
      key={moment.key}
      className="pr-screen"
      aria-hidden
      style={{ "--pr-delay": `${moment.delay}ms` } as CSSProperties}
      onAnimationEnd={(e) => {
        if (e.animationName === "pr-edge") setDoneKey(moment.key)
      }}
    />
  )
}
