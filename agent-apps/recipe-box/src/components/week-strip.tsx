import { ListChecks, ReceiptText } from "lucide-react"
import { DAY_SHORT, type ListRecord, type Slot } from "@/lib/box"
import type { Item } from "@/hooks/use-box"
import { COPY } from "@/lib/copy"

interface Props {
  slots: Slot[]
  items: Item[]
  glow: boolean
  live: boolean
  list: ListRecord | null
  note: string | null
  onPlan: () => void
  onList: () => void
  onRecipe: (item: Item) => void
}

export function WeekStrip(p: Props) {
  const byDay = (day: string) => p.items.filter((x) => x.shown.status === "week" && x.shown.day === day)
  // A phone shows the two buttons in a row above all seven days; a wide screen puts them at the strip's right end.
  return (
    <footer className="strip" data-glow={p.glow || undefined} aria-label="This week">
      <div className="relative z-10 mx-auto flex h-full flex-col-reverse gap-1.5 px-2 py-2 md:flex-row md:items-stretch md:gap-4 md:px-6 md:py-0">
        <div className="slots grid min-w-0 flex-1 grid-cols-7 gap-1 md:gap-3 md:py-3">
          {p.slots.map((s) => {
            const here = byDay(s.day)
            const first = here[0]
            return (
              <div
                key={s.day}
                data-slot={s.day}
                data-today={s.today || undefined}
                className="slot flex min-w-0 flex-col items-center justify-between gap-1 px-0.5 py-1.5 md:gap-0 md:px-1.5 md:py-2"
              >
                <div className="flex items-baseline gap-1 text-[0.6875rem] font-semibold uppercase tracking-[0.06em] md:tracking-[0.08em]">
                  <span className="md:hidden">{DAY_SHORT[s.day][0]}</span>
                  <span className="hidden md:inline">{DAY_SHORT[s.day]}</span>
                  <span className="font-medium tabular-nums text-[var(--strip-ink-soft)]">{s.date.getDate()}</span>
                </div>
                <div data-slot-target className="relative size-9 md:size-[3.25rem]">
                  {first ? (
                    <button
                      type="button"
                      className="block size-full"
                      onClick={() => p.onRecipe(first)}
                      aria-label={`${DAY_SHORT[s.day]}: ${here.map((x) => x.record.body.title).join(", ")}`}
                    >
                      {here.slice(0, 2).reverse().map((x, n, all) => (
                        <span
                          key={x.record.id}
                          className={
                            "slot-thumb absolute overflow-hidden rounded-full " +
                            (all.length > 1 && n === 0 ? "-right-1.5 -top-1 size-[70%] opacity-90" : "inset-0")
                          }
                          style={{ background: x.record.body.color }}
                        >
                          <img src={x.record.body.image} alt="" draggable={false} className="size-full object-cover" />
                        </span>
                      ))}
                    </button>
                  ) : (
                    <span className="slot-empty block size-full rounded-full" />
                  )}
                </div>
                <div className="hidden w-full truncate text-center text-xs leading-tight md:block">
                  {first ? (
                    <>
                      {first.record.body.title}
                      {here.length > 1 && <span className="text-[var(--strip-ink-soft)]"> +{here.length - 1}</span>}
                    </>
                  ) : (
                    <span className="text-[var(--strip-ink-soft)]">{COPY.openDay}</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        <div className="flex shrink-0 items-center gap-1.5 md:w-52 md:flex-col md:items-stretch md:justify-center md:gap-2 md:py-2.5">
          <button
            type="button"
            onClick={p.onPlan}
            disabled={!p.live || p.glow}
            className="flex h-9 flex-1 items-center justify-center gap-1.5 rounded-xl bg-primary px-3 text-[0.8125rem] font-semibold leading-tight text-primary-foreground shadow-[0_6px_14px_-6px_rgb(0_0_0/0.5),inset_0_1px_0_rgb(255_255_255/0.25)] transition-transform active:scale-[0.97] disabled:cursor-default disabled:opacity-100 md:h-auto md:min-h-11 md:flex-none md:text-sm"
          >
            <ListChecks className="size-4" aria-hidden />
            {p.glow ? (
              <span>
                {COPY.making}<span className="status-dot">…</span>
              </span>
            ) : (
              <span>{COPY.planWeek}</span>
            )}
          </button>
          <button
            type="button"
            onClick={p.onList}
            disabled={!p.list}
            className="flex h-9 shrink-0 items-center justify-center gap-1.5 rounded-xl border border-[var(--slot-well-edge)] bg-[var(--strip-button)] px-3 text-xs font-semibold text-[var(--strip-ink)] transition-transform active:scale-[0.97] disabled:opacity-50 md:h-auto md:min-h-9 md:text-[0.8125rem]"
          >
            <ReceiptText className="size-4" aria-hidden />
            {p.list ? (
              <span>
                {COPY.list}<span className="hidden md:inline"> · {p.list.body.items.length} items</span>
              </span>
            ) : (
              COPY.noList
            )}
          </button>
          {p.note && <p className="text-center text-[0.6875rem] leading-tight">{p.note}</p>}
        </div>
      </div>
    </footer>
  )
}
