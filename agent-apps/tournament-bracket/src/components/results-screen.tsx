import { roundName, type Bracket, type Played, type Results } from "@/lib/bracket"
import type { Copy } from "@/lib/config"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { MatchOptions, navigate } from "@/components/match-options"

type Props = {
  bracket: Bracket
  played: Map<string, Played>
  results: Results
  copy: Copy
  onResult: (match: string, winner: string | null, score?: string) => void
}

/** The commissioner's screen: the winner of each match and its score, as the games finish. */
export function ResultsScreen({ bracket, played, results, copy, onResult }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <div>
        <h2 className="display text-4xl uppercase">{copy.results}</h2>
        <p className="text-sm text-muted-foreground">{copy.resultsHint}</p>
      </div>
      <div className="grid gap-x-4 gap-y-6 md:grid-cols-2 xl:grid-cols-4" onKeyDown={navigate}>
        {bracket.byRound.map((matches, ri) => (
          <section key={ri} className="flex flex-col gap-2.5">
            <h3 className="display text-xl text-muted-foreground uppercase">{roundName(ri + 1, bracket.rounds)}</h3>
            {matches.map((m) => {
              const p = played.get(m.id)!
              const r = results[m.id]
              const ready = !!(p.players[0] && p.players[1])
              return (
                <MatchOptions
                  key={m.id}
                  id={m.id}
                  label={m.id}
                  players={p.players}
                  chosen={p.winner?.name}
                  locked={false}
                  waiting={copy.waiting}
                  onChoose={(name) => onResult(m.id, name, r?.score)}
                  extra={
                    ready && (
                      <div className="flex gap-1.5">
                        <Input
                          aria-label={`${copy.scorePlaceholder} ${m.id}`}
                          placeholder={copy.scorePlaceholder}
                          className="h-9"
                          value={r?.score ?? ""}
                          disabled={!p.winner}
                          onChange={(e) => p.winner && onResult(m.id, p.winner.name, e.target.value)}
                        />
                        <Button variant="ghost" className="h-9" disabled={!p.winner} onClick={() => onResult(m.id, null)}>
                          {copy.clear}
                        </Button>
                      </div>
                    )
                  }
                />
              )
            })}
          </section>
        ))}
      </div>
    </div>
  )
}
