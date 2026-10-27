import { ArrowRightIcon } from "lucide-react"
import { projected, roundName, type Bracket, type Picks, type Played } from "@/lib/bracket"
import type { Copy } from "@/lib/config"
import { Button } from "@/components/ui/button"
import { MatchOptions, navigate } from "@/components/match-options"

type Props = {
  bracket: Bracket
  played: Map<string, Played>
  people: string[]
  picks: Picks
  person: number
  copy: Copy
  onPerson: (i: number) => void
  onPick: (person: string, match: string, name: string) => void
}

/** Hot-seat picks: one person fills the whole bracket, then passes the device on. */
export function PicksScreen({ bracket, played, people, picks, person, copy, onPerson, onPick }: Props) {
  if (!people.length) return <p className="py-10 text-center text-muted-foreground">{copy.noPeople}</p>
  const who = people[person] ?? people[0]
  const mine = picks[who] ?? {}
  const proj = projected(bracket, mine)
  const made = bracket.matches.filter((m) => mine[m.id]).length
  const next = people[(person + 1) % people.length]

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label={copy.picksFor}>
        {people.map((p, i) => {
          const count = bracket.matches.filter((m) => picks[p]?.[m.id]).length
          return (
            <button
              key={p}
              type="button"
              role="tab"
              aria-selected={i === person}
              onClick={() => onPerson(i)}
              className="surface flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors aria-selected:border-primary aria-selected:bg-primary aria-selected:text-primary-foreground active:scale-[0.97]"
            >
              {p}
              <span className="figure text-xs opacity-75">
                {count}/{bracket.matches.length}
              </span>
            </button>
          )
        })}
      </div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="display text-4xl uppercase">
            {copy.picksFor} {who}
          </h2>
          <p className="text-sm text-muted-foreground">{made === bracket.matches.length ? copy.picksDone : copy.picksHint}</p>
        </div>
        {people.length > 1 && (
          <Button size="lg" onClick={() => onPerson((person + 1) % people.length)}>
            {copy.passTo} {next}
            <ArrowRightIcon />
          </Button>
        )}
      </div>
      <div className="grid gap-x-4 gap-y-6 md:grid-cols-2 xl:grid-cols-4" onKeyDown={navigate}>
        {bracket.byRound.map((matches, ri) => (
          <section key={ri} className="flex flex-col gap-2.5">
            <h3 className="display text-xl text-muted-foreground uppercase">
              {roundName(ri + 1, bracket.rounds)} · {matches[0].points} {matches[0].points === 1 ? "pt" : "pts"}
            </h3>
            {matches.map((m) => {
              const p = played.get(m.id)!
              const chosen = mine[m.id]
              const note = p.winner && chosen ? chosen === p.winner.name ? <span className="text-win normal-case">+{m.points}</span> : <span className="normal-case">+0</span> : null
              return (
                <MatchOptions
                  key={m.id}
                  id={m.id}
                  label={m.id}
                  players={proj.get(m.id)!}
                  chosen={chosen}
                  locked={!!p.winner}
                  note={note}
                  waiting={copy.waiting}
                  onChoose={(name) => onPick(who, m.id, name)}
                />
              )
            })}
          </section>
        ))}
      </div>
    </div>
  )
}
