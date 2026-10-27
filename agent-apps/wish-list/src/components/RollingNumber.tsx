import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

const CELLS = Array.from({ length: 20 }, (_, n) => n % 10)

/**
 * One digit: a strip of 0 to 9 twice, so a new turn rolls a whole lap before it lands. The leading digit rolls up from
 * one within the first lap, so it never shows a zero.
 */
function Digit({ digit, turn, delay, leading }: { digit: number; turn: number; delay: number; leading: boolean }) {
  const target = leading ? digit : digit + (turn % 2) * 10
  const [at, setAt] = useState(leading ? Math.min(1, digit) : 0)
  useEffect(() => {
    const frame = requestAnimationFrame(() => setAt(target))
    return () => cancelAnimationFrame(frame)
  }, [target])
  return (
    <span className="roll-col" aria-hidden="true">
      <span
        className="roll-strip"
        style={{ transform: `translateY(${-at * 1.1}em)`, "--roll-delay": `${delay}ms` } as React.CSSProperties}
      >
        {CELLS.map((n, i) => (
          <span key={i}>{n}</span>
        ))}
      </span>
    </span>
  )
}

/**
 * A figure whose digits roll to their value: from zero when it first shows, to the new value when it changes, and a
 * full lap when `turn` moves on.
 */
export function RollingNumber({
  value,
  format,
  turn = 0,
  className,
}: {
  value: number
  format: Intl.NumberFormat
  turn?: number
  className?: string
}) {
  const text = format.format(value)
  const chars = [...text]
  const digits = chars.filter((c) => /\d/.test(c)).length
  let fromRight = digits
  return (
    <span className={cn("roll", className)} role="text" aria-label={text}>
      {chars.map((c, i) => {
        const key = chars.length - i
        if (/\d/.test(c)) {
          fromRight -= 1
          return <Digit key={`d${key}`} digit={Number(c)} turn={turn} delay={fromRight * 45} leading={fromRight === digits - 1} />
        }
        return (
          <span key={`c${key}`} aria-hidden="true">
            {c}
          </span>
        )
      })}
    </span>
  )
}
