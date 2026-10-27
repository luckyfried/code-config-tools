import { useLayoutEffect, useRef } from "react"
import { cn } from "@/lib/utils"
import type { Bracket, Standing } from "@/lib/bracket"
import type { Copy } from "@/lib/config"
import { SPRING } from "@/lib/motion"
import { teamStyle } from "@/components/bracket-svg"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

/** Moves each row from where it was to where it is now (FLIP), so a change in the order reads as people passing. */
function useFlip(order: string, reduced: boolean) {
  const nodes = useRef(new Map<string, HTMLElement>())
  const rects = useRef(new Map<string, DOMRect>())
  useLayoutEffect(() => {
    const next = new Map<string, DOMRect>()
    for (const [key, el] of nodes.current) next.set(key, el.getBoundingClientRect())
    if (!reduced) {
      for (const [key, el] of nodes.current) {
        const was = rects.current.get(key)
        const now = next.get(key)!
        if (!was) continue
        const dx = was.left - now.left
        const dy = was.top - now.top
        if (Math.abs(dx) < 1 && Math.abs(dy) < 1) continue
        el.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], { duration: SPRING.flip.ms + 80, easing: SPRING.flip.easing })
      }
    }
    rects.current = next
  }, [order, reduced])
  return (key: string) => (el: HTMLElement | null) => {
    if (el) nodes.current.set(key, el)
    else nodes.current.delete(key)
  }
}

type Props = { standings: Standing[]; bracket: Bracket; copy: Copy; reduced: boolean }

function rankOf(standings: Standing[], i: number) {
  let r = i
  while (r > 0 && standings[r - 1].points === standings[i].points) r--
  return r + 1
}

/** The pool across the foot of the desktop bracket: one card per person, best first. */
export function PoolStrip({ standings, copy, reduced }: Props) {
  const ref = useFlip(standings.map((s) => s.person).join("|"), reduced)
  const lead = standings[0]?.points ?? 0
  return (
    <ol className="grid gap-3" style={{ gridTemplateColumns: `repeat(${Math.max(1, standings.length)}, minmax(0, 1fr))` }} aria-label={copy.pool}>
      {standings.map((s, i) => (
        <li key={s.person} ref={ref(s.person)} className={cn("surface relative flex min-w-0 items-center gap-3 rounded-xl px-4 py-3", i === 0 && lead > 0 && "ring-2 ring-win")}>
          <span className="display figure w-7 shrink-0 text-3xl text-muted-foreground">{rankOf(standings, i)}</span>
          <span className="flex min-w-0 flex-1 flex-col gap-0.5">
            <span className="truncate text-base font-semibold">{s.person}</span>
            <span className="flex min-w-0 items-center gap-1.5 text-xs text-muted-foreground">
              {s.champion && <span className="team-bar size-2 shrink-0 rounded-full" style={teamStyle(s.champion.color)} />}
              <span className="truncate">{s.champion ? s.champion.name : "—"}</span>
            </span>
          </span>
          <span className="flex shrink-0 flex-col items-end">
            <span key={s.points} className="display figure text-3xl animate-in zoom-in-90 duration-300">
              {s.points}
            </span>
            <span className="figure text-[0.7rem] text-muted-foreground">
              {s.correct}/{s.decided}
            </span>
          </span>
        </li>
      ))}
    </ol>
  )
}

/** The pool as a list for the phone. */
export function PoolList({ standings, copy, reduced }: Props) {
  const ref = useFlip(standings.map((s) => s.person).join("|"), reduced)
  return (
    <ol className="flex flex-col gap-2" aria-label={copy.pool}>
      {standings.map((s, i) => (
        <li key={s.person} ref={ref(s.person)} className="surface flex items-center gap-3 rounded-xl px-4 py-3">
          <span className="display figure w-6 text-2xl text-muted-foreground">{rankOf(standings, i)}</span>
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-base font-semibold">{s.person}</span>
            <span className="flex min-w-0 items-center gap-1.5 text-sm text-muted-foreground">
              {s.champion && <span className="team-bar size-2 shrink-0 rounded-full" style={teamStyle(s.champion.color)} />}
              <span className="truncate">{s.champion ? s.champion.name : "—"}</span>
            </span>
          </span>
          <span className="flex flex-col items-end">
            <span key={s.points} className="display figure text-3xl animate-in zoom-in-90 duration-300">
              {s.points}
            </span>
            <span className="figure text-xs text-muted-foreground">
              {s.correct}/{s.decided}
            </span>
          </span>
        </li>
      ))}
    </ol>
  )
}

/** The pool in one row under the phone's rounds: every person, best first. */
export function PoolPills({ standings, copy, reduced }: Props) {
  const ref = useFlip(standings.map((s) => s.person).join("|"), reduced)
  return (
    <ol className="grid gap-1.5 px-4" style={{ gridTemplateColumns: `repeat(${Math.max(1, Math.min(6, standings.length))}, minmax(0, 1fr))` }} aria-label={copy.pool}>
      {standings.slice(0, 6).map((s, i) => (
        <li key={s.person} ref={ref(s.person)} className={cn("surface flex min-w-0 flex-col items-center rounded-lg px-1 py-1", i === 0 && s.points > 0 && "ring-2 ring-win")}>
          <span className="w-full truncate text-center text-xs font-semibold">{s.person}</span>
          <span key={s.points} className="display figure text-xl leading-none animate-in zoom-in-90 duration-300">
            {s.points}
          </span>
        </li>
      ))}
    </ol>
  )
}

/** The Pool screen: the full table. */
export function PoolTable({ standings, copy, reduced }: Props) {
  const ref = useFlip(standings.map((s) => s.person).join("|"), reduced)
  return (
    <Table className="text-base">
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">#</TableHead>
          <TableHead>{copy.pool}</TableHead>
          <TableHead className="text-right">{copy.points}</TableHead>
          <TableHead className="text-right">{copy.correct}</TableHead>
          <TableHead className="hidden text-right sm:table-cell">{copy.maxPossible}</TableHead>
          <TableHead className="hidden md:table-cell">{copy.championPick}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {standings.map((s, i) => (
          <TableRow key={s.person} ref={ref(s.person)}>
            <TableCell className="display figure text-2xl text-muted-foreground">{rankOf(standings, i)}</TableCell>
            <TableCell className="font-semibold">{s.person}</TableCell>
            <TableCell className="display figure text-right text-2xl">{s.points}</TableCell>
            <TableCell className="figure text-right">
              {s.correct}/{s.decided}
            </TableCell>
            <TableCell className="figure hidden text-right sm:table-cell">{s.possible}</TableCell>
            <TableCell className="hidden md:table-cell">
              {s.champion ? (
                <span className="inline-flex items-center gap-2">
                  <span className="team-bar size-2.5 rounded-full" style={teamStyle(s.champion.color)} />
                  {s.champion.name}
                </span>
              ) : (
                "—"
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
