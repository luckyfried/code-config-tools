// Thirty bars, one a day from today: cards coming back in the deep tone, new cards in the bright one. Heights are a
// scale on each bar, so a re-tally eases every bar to its new height. The scale only ever rises while the chart is
// open, so answering a card shrinks today's bar and grows the bar of its new date while every other bar holds still.

import { useEffect, useState } from "react"
import { monthDay, weekday } from "@/lib/dates"
import type { ForecastDay } from "@/lib/session"

export function ForecastChart({ days, height, labels = true, grow }: { days: ForecastDay[]; height: number; labels?: boolean; grow: boolean }) {
  const [shown, setShown] = useState(!grow)
  useEffect(() => {
    if (shown) return
    const id = requestAnimationFrame(() => requestAnimationFrame(() => setShown(true)))
    return () => cancelAnimationFrame(id)
  }, [shown])
  const [top, setTop] = useState(6)
  const need = Math.max(6, ...days.map((d) => d.seen + d.fresh))
  if (need > top) setTop(need)
  const max = Math.max(top, need)

  return (
    <div className="flex flex-col">
      <div className="bars flex items-end gap-[3px]" style={{ height }} role="img" aria-label={`Cards coming up each of the next ${days.length} days`}>
        {days.map((d, i) => {
          const total = d.seen + d.fresh
          return (
            <div key={d.day} className="bar-track relative h-full flex-1 overflow-hidden rounded-t-[3px]" title={`${i === 0 ? "Today" : `${weekday(d.day)} ${monthDay(d.day)}`}: ${total} card${total === 1 ? "" : "s"}`}>
              <div
                className="bar bar-new absolute inset-0 rounded-t-[3px]"
                style={{ "--h": shown ? total / max : 0, "--delay": grow ? `${i * 18}ms` : "0ms" } as React.CSSProperties}
              />
              <div
                className="bar bar-due absolute inset-0 rounded-t-[3px]"
                style={{ "--h": shown ? d.seen / max : 0, "--delay": grow ? `${i * 18}ms` : "0ms" } as React.CSSProperties}
              />
            </div>
          )
        })}
      </div>
      {labels ? (
        <div className="paper-row tnum justify-between text-[11px] text-face-soft">
          <span>Today</span>
          <span>{monthDay(days[Math.min(9, days.length - 1)].day)}</span>
          <span>{monthDay(days[Math.min(19, days.length - 1)].day)}</span>
          <span>{monthDay(days[days.length - 1].day)}</span>
        </div>
      ) : null}
    </div>
  )
}

export function ForecastKey() {
  return (
    <div className="flex items-center gap-3 text-xs text-face-soft">
      <span className="flex items-center gap-1.5">
        <span className="bar-due size-2.5 rounded-[3px]" /> Coming back
      </span>
      <span className="flex items-center gap-1.5">
        <span className="bar-new size-2.5 rounded-[3px]" /> New
      </span>
    </div>
  )
}
