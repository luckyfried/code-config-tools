import { useRef } from "react"
import { roundName, type Bracket, type Played } from "@/lib/bracket"
import type { Copy } from "@/lib/config"
import { scoreFor, teamStyle } from "@/components/bracket-svg"

type Props = { bracket: Bracket; played: Map<string, Played>; copy: Copy; reduced: boolean }

/** The phone's bracket: one round per panel, snapping sideways, with a dot for each round in the header. */
export function RoundsView({ bracket, played, copy, reduced }: Props) {
  const scroller = useRef<HTMLDivElement>(null)

  const show = (i: number) => {
    const el = scroller.current
    const panel = el?.children[i] as HTMLElement | undefined
    if (el && panel) el.scrollTo({ left: panel.offsetLeft - el.offsetLeft, behavior: reduced ? "auto" : "smooth" })
  }

  const byeIn = (round: number) => (round === 2 ? bracket.byes.length : 0)

  return (
    <div ref={scroller} className="snap-rounds flex min-h-0 flex-1 overflow-x-auto overflow-y-hidden pb-2" aria-label={copy.bracket}>
      {bracket.byRound.map((matches, ri) => {
        const round = ri + 1
        const done = matches.filter((m) => played.get(m.id)?.winner).length
        return (
          <section key={round} className="flex w-full shrink-0 flex-col px-4" aria-label={roundName(round, bracket.rounds)}>
            <header className="flex items-center justify-between gap-3 pb-1.5">
              <h2 className="display min-w-0 truncate text-2xl uppercase">{roundName(round, bracket.rounds)}</h2>
              <span className="figure shrink-0 text-sm text-muted-foreground">
                {done}/{matches.length}
                {byeIn(round) > 0 && ` · ${byeIn(round)} ${copy.bye.toLowerCase()}`}
              </span>
              <span className="flex shrink-0 items-center" role="group" aria-label={copy.bracket}>
                {bracket.byRound.map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => show(i)}
                    aria-label={roundName(i + 1, bracket.rounds)}
                    aria-current={i === ri ? "step" : undefined}
                    className="grid size-6 place-items-center"
                  >
                    <span className={`block h-2 rounded-full transition-all duration-300 ${i === ri ? "w-5 bg-foreground" : "w-2 bg-muted-foreground/40"}`} />
                  </button>
                ))}
              </span>
            </header>
            <ol className="flex min-h-0 flex-1 flex-col justify-around gap-2.5 overflow-y-auto">
              {matches.map((m) => {
                const p = played.get(m.id)!
                return (
                  <li key={m.id} className="relative pr-5">
                    <MatchCard played={p} copy={copy} />
                    <span aria-hidden className="match-link absolute top-[15px] right-1.5 bottom-[15px] w-2.5 rounded-r-md border-y-2 border-r-2" data-live={!!p.winner} />
                    {m.next && <span aria-hidden className="match-link absolute top-1/2 right-0 w-1.5 border-t-2" data-live={!!p.winner} />}
                  </li>
                )
              })}
            </ol>
          </section>
        )
      })}
    </div>
  )
}

function MatchCard({ played: p, copy }: { played: Played; copy: Copy }) {
  const winnerSlot = p.winner && p.players[0]?.name === p.winner.name ? 0 : 1
  return (
    <div className="flex flex-col gap-[3px]">
      {[0, 1].map((slot) => {
        const e = p.players[slot]
        const state = !e ? "empty" : p.winner ? (p.winner.name === e.name ? "won" : "lost") : "open"
        const upset = p.upset && state === "lost"
        return (
          <div key={slot} className="card-row flex h-[30px] items-center gap-2 overflow-hidden rounded-md pr-3" data-state={state} data-upset={upset} style={e ? teamStyle(e.color) : undefined}>
            <span className="team-bar h-full w-1.5 shrink-0" />
            {e ? (
              <>
                <span className="figure w-5 text-right text-xs opacity-80">{e.seed}</span>
                <span className={`min-w-0 flex-1 truncate text-[0.9rem] ${upset ? "line-through decoration-upset decoration-2" : ""}`}>{e.name}</span>
                {state === "won" && p.upset && <span className="rounded-full bg-upset px-1.5 py-px text-[0.6rem] font-extrabold tracking-wide text-[var(--upset-foreground)] uppercase">{copy.upset}</span>}
                {p.winner && <span className="figure text-sm font-bold">{scoreFor(p.score, slot, winnerSlot)}</span>}
              </>
            ) : (
              <span className="min-w-0 flex-1 truncate pl-1 text-sm">{copy.waiting}</span>
            )}
          </div>
        )
      })}
    </div>
  )
}
