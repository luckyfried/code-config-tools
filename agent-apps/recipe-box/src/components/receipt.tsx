import { useLayoutEffect, useRef, useState } from "react"
import { X } from "lucide-react"
import { quantity, type ListRecord } from "@/lib/box"
import { reduced } from "@/lib/motion"
import type { Day } from "@/types"

interface Props {
  list: ListRecord
  name: string
  household: number
  titles: Record<string, { title: string; day: Day | null }>
  ticked: string[]
  onTick: (line: string) => void
  onClose: () => void
}

const lineId = (name: string, unit: string | null) => `${name}|${unit ?? ""}`
const SLASHED: Record<string, string> = { "¼": "1/4", "½": "1/2", "¾": "3/4", "⅓": "1/3", "⅔": "2/3" }
// A till prints its fractions with a slash, "1 1/2 tbsp".
const tillAmount = (text: string) => text.replace(/(\d?)([¼½¾⅓⅔])/g, (_, d: string, f: string) => (d ? `${d} ` : "") + SLASHED[f])

// The week's shopping list as a till receipt, grouped by aisle; a tapped line is struck through.
export function Receipt(p: Props) {
  const [closing, setClosing] = useState(false)
  const paper = useRef<HTMLDivElement>(null)
  // The paper feeds up out of the slot in the shelf a line at a time, the way a till prints: the shop's name first,
  // then each aisle heading with its lines under it.
  useLayoutEffect(() => {
    const el = paper.current
    if (!el || reduced()) return
    const h = el.offsetHeight
    const lines = Math.max(6, Math.round(h / 21))
    el.animate([{ transform: `translateY(${h}px)` }, { transform: "translateY(0)" }], {
      duration: Math.min(2600, lines * 70),
      easing: `steps(${lines}, jump-start)`,
    })
  }, [])
  const l = p.list.body
  const groups: { aisle: string; items: typeof l.items }[] = []
  for (const item of l.items) {
    const g = groups.at(-1)
    if (g && g.aisle === item.aisle) g.items.push(item)
    else groups.push({ aisle: item.aisle, items: [item] })
  }
  const weekOf = new Date(`${l.week_of}T12:00:00`).toLocaleDateString("en-US", { month: "long", day: "numeric" })
  const made = new Date(l.made_at).toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })
  const left = l.items.filter((x) => !p.ticked.includes(lineId(x.name, x.unit))).length
  const close = () => {
    setClosing(true)
    window.setTimeout(p.onClose, 360)
  }
  return (
    <>
    {/* On a phone the list covers the box, so the box dims behind it and a tap on it puts the list away. */}
    <div
      className="fixed inset-x-0 top-0 z-[24] bg-[var(--overlay)] transition-opacity duration-300 animate-in fade-in md:hidden data-[closing]:opacity-0"
      style={{ bottom: "calc(var(--strip-h) + env(safe-area-inset-bottom))" }}
      data-closing={closing || undefined}
      onClick={close}
      aria-hidden
    />
    <div className="receipt-slot inset-x-1 md:left-auto md:right-5 md:w-[23rem]" aria-hidden />
    <div className="receipt-mouth inset-x-2 md:left-auto md:right-6 md:w-[22rem]" role="dialog" aria-label={`Shopping list for the week of ${weekOf}`}>
      <div
        ref={paper}
        className="receipt relative max-h-[calc(100dvh-var(--strip-h)-env(safe-area-inset-bottom)-10rem)] overflow-y-auto overscroll-contain px-5 pb-5 pt-6 font-mono text-[0.8125rem] leading-relaxed md:max-h-[min(36rem,calc(100dvh-var(--strip-h)-2rem))]"
        data-closing={closing || undefined}
      >
        <button
          type="button"
          onClick={close}
          className="absolute right-3 top-4 grid size-8 place-items-center rounded-full text-[var(--receipt-faint)] hover:bg-black/5 hover:text-[var(--receipt-ink)]"
          aria-label="Put the list away"
        >
          <X className="size-4" />
        </button>
        <div className="text-center">
          <div className="text-[0.95rem] font-semibold uppercase tracking-[0.3em]">Recipe Box</div>
          <div className="mt-0.5 uppercase tracking-[0.12em] text-[var(--receipt-faint)]">Week of {weekOf}</div>
          <div className="text-[var(--receipt-faint)]">
            {p.name ? `${p.name} · ` : ""}
            {p.household} {p.household === 1 ? "person" : "people"}
          </div>
        </div>
        <hr className="dashed-rule my-3" />
        {groups.map((g) => (
          <section key={g.aisle} className="mb-2.5">
            <h4 className="mb-0.5 text-[0.6875rem] font-semibold uppercase tracking-[0.22em] text-[var(--receipt-faint)]">{g.aisle}</h4>
            <ul>
              {g.items.map((item) => {
                const id = lineId(item.name, item.unit)
                const on = p.ticked.includes(id)
                return (
                  <li key={id}>
                    <button
                      type="button"
                      onClick={() => p.onTick(id)}
                      aria-pressed={on}
                      className="receipt-line flex w-full items-baseline gap-3 py-[1px] text-left"
                      data-ticked={on || undefined}
                    >
                      <span className="min-w-0 flex-1">{item.name}</span>
                      <span className="shrink-0 tabular-nums">{tillAmount(quantity(item.amount, item.unit))}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </section>
        ))}
        <hr className="dashed-rule my-3" />
        <div className="flex justify-between font-semibold uppercase tracking-[0.08em]">
          <span>{l.items.length} items</span>
          <span>{left} to get</span>
        </div>
        <ul className="mt-2 text-[var(--receipt-faint)]">
          {l.recipes.map((id) => (
            <li key={id} className="truncate">
              {p.titles[id]?.day ? `${p.titles[id].day!.toUpperCase()}  ` : ""}
              {p.titles[id]?.title ?? id}
            </li>
          ))}
        </ul>
        <div className="mt-3 text-center text-[0.6875rem] uppercase tracking-[0.18em] text-[var(--receipt-faint)]">Made {made}</div>
      </div>
    </div>
    </>
  )
}
