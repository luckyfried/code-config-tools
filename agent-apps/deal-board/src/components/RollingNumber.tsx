import { cn } from "@/lib/utils"

const DIGITS = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

/** A number whose digits roll to their new places when it changes, like an odometer. */
export function RollingNumber({ value, format, className }: { value: number; format: (value: number) => string; className?: string }) {
  const text = format(value)
  const chars = [...text]
  return (
    <span className={cn("inline-flex tabular-nums", className)}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true" className="roll">
        {chars.map((char, i) => {
          // Keyed from the right, so the ones stay the ones when the number grows a digit.
          const place = chars.length - i
          return /\d/.test(char) ? <Digit key={`d${place}`} digit={Number(char)} /> : <span key={`c${place}-${char}`} className="roll-char">
              {char}
            </span>
        })}
      </span>
    </span>
  )
}

function Digit({ digit }: { digit: number }) {
  return (
    <span className="roll-digit">
      <span className="roll-strip" style={{ "--digit": digit } as React.CSSProperties}>
        {DIGITS.map((d) => (
          <span key={d}>{d}</span>
        ))}
      </span>
    </span>
  )
}
