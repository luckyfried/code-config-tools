import type { CSSProperties } from "react"
import { cn } from "@/lib/utils"

const DIGITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

/** A whole number whose digits roll to their places, odometer style; columns are keyed from the right. */
export function RollingNumber({ value, className }: { value: number; className?: string }) {
  const text = String(Math.max(0, Math.round(value)))
  const columns = text.split("").map((ch, i) => ({ d: Number(ch), place: text.length - 1 - i }))
  return (
    <span className={cn("inline-flex tabular-nums", className)}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true" className="inline-flex">
        {columns.map(({ d, place }) => (
          <span key={place} className="roll-digit">
            <span className="roll-strip" style={{ "--d": d } as CSSProperties}>
              {DIGITS.map((n) => (
                <span key={n} className="block h-[1em]">
                  {n}
                </span>
              ))}
            </span>
          </span>
        ))}
      </span>
    </span>
  )
}
