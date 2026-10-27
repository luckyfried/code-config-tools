// One square a day, darker for more cards answered, filled from the oldest day to today. As weeks it is a grid of
// seven rows; as a strip it is one row of the last days.

import { addDays, monthDay, parseDay } from "@/lib/dates"
import type { DayLog } from "@/lib/config"

const level = (n: number) => (n <= 0 ? 0 : n < 6 ? 1 : n < 12 ? 2 : n < 20 ? 3 : 4)
// Today's square is keyed on its level, so the moment an answer moves it up a shade it fills in again, at once.
const cellKey = (day: string, now: string, n: number) => (day === now ? `${day}:${level(n)}` : day)
const cellDelay = (day: string, now: string, n: number, animate: boolean, ms: number) =>
  animate && !(day === now && n > 0) ? `${ms}ms` : "0ms"

export function HeatWeeks({ log, now, weeks, cell = 14, animate }: { log: Record<string, DayLog>; now: string; weeks: number; cell?: number; animate: boolean }) {
  const dow = (parseDay(now).getDay() + 6) % 7
  const start = addDays(now, -(weeks - 1) * 7 - dow)
  const total = (weeks - 1) * 7 + dow + 1
  const cols: { day: string; i: number }[][] = []
  for (let i = 0; i < weeks * 7; i++) {
    const day = addDays(start, i)
    ;(cols[Math.floor(i / 7)] ??= []).push({ day, i })
  }
  // A month is named over the first week that holds its first day; labels closer than three weeks apart drop the
  // earlier one, so names never run together.
  const months = cols.map((c) => {
    const first = c.find(({ day }) => parseDay(day).getDate() === 1)
    return first ? monthDay(first.day).split(" ")[0] : ""
  })
  let last = -9
  for (let k = 0; k < months.length; k++) {
    if (!months[k]) continue
    if (k - last < 3 && last >= 0) months[last] = ""
    last = k
  }
  const gap = Math.max(2, Math.round(cell / 5))
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex text-[11px] text-face-soft" style={{ gap }}>
        {months.map((m, k) => (
          <span key={k} className="overflow-visible whitespace-nowrap" style={{ width: cell }}>
            {m}
          </span>
        ))}
      </div>
      <div className="flex" style={{ gap }} role="img" aria-label={`Cards answered each day for the last ${weeks} weeks`}>
        {cols.map((c, k) => (
          <div key={k} className="flex flex-col" style={{ gap }}>
            {c.map(({ day, i }) => {
              const future = i >= total
              const n = log[day]?.seen ?? 0
              return (
                <span
                  key={cellKey(day, now, n)}
                  className="heat block"
                  data-l={future ? undefined : level(n)}
                  data-today={day === now ? "" : undefined}
                  title={future ? undefined : `${monthDay(day)}: ${n} answered`}
                  style={{ width: cell, height: cell, opacity: future ? 0 : undefined, "--delay": cellDelay(day, now, n, animate, Math.max(0, i - (total - 42)) * 26) } as React.CSSProperties}
                />
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

export function HeatRow({ log, now, days, animate }: { log: Record<string, DayLog>; now: string; days: number; animate: boolean }) {
  return (
    <div className="flex w-full justify-between gap-[3px]" role="img" aria-label={`Cards answered each of the last ${days} days`}>
      {Array.from({ length: days }, (_, i) => {
        const day = addDays(now, i - days + 1)
        const n = log[day]?.seen ?? 0
        return (
          <span
            key={cellKey(day, now, n)}
            className="heat block aspect-square max-w-4 flex-1"
            data-l={level(n)}
            data-today={day === now ? "" : undefined}
            style={{ "--delay": cellDelay(day, now, n, animate, i * 34) } as React.CSSProperties}
          />
        )
      })}
    </div>
  )
}
