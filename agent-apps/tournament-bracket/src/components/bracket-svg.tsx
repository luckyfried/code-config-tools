import { useLayoutEffect, useRef, useState, type CSSProperties } from "react"
import { roundName, type Bracket, type Entrant, type Played } from "@/lib/bracket"
import type { Copy } from "@/lib/config"
import { CHAMP_H, CHAMP_W, CHIP_H, CHIP_W, MATCH_H, fit, inkOn, luminance, truncate, type Layout } from "@/lib/layout"
import { SPRING } from "@/lib/motion"
import { ChampionBanner } from "@/components/champion-banner"

type Ghost = { key: string; entrant: Entrant; from: { x: number; y: number }; to: { x: number; y: number }; champion: boolean }

type Props = {
  bracket: Bracket
  layout: Layout
  played: Map<string, Played>
  copy: Copy
  reduced: boolean
  width: number
  onChampion?: (entrant: Entrant, at: DOMRect | null) => void
}

/** --team-lift is the entrant's color raised to a mid lightness of the same hue when it is too dark to read as a fill
 * on a dark theme; a dark theme uses it through --lift. */
export function teamStyle(color: string): CSSProperties {
  const lift = luminance(color) < 0.06 ? `oklch(from ${color} 0.52 calc(c + 0.04) h)` : color
  return { "--team": color, "--team-lift": lift, "--team-ink": inkOn(color) } as CSSProperties
}

export function BracketSvg({ bracket, layout: L, played, copy, reduced, width, onChampion }: Props) {
  const finalId = bracket.byRound[bracket.rounds - 1][0].id
  const prev = useRef<Map<string, string | null> | null>(null)
  const [ghosts, setGhosts] = useState<Ghost[]>([])
  const [arriving, setArriving] = useState<Set<string>>(new Set())
  const [cheer, setCheer] = useState(0)
  const bannerRef = useRef<HTMLDivElement>(null)

  // A winner who is new since the last render slides from their chip along the line into the next slot.
  useLayoutEffect(() => {
    const now = new Map([...played].map(([id, p]) => [id, p.winner?.name ?? null]))
    const before = prev.current
    prev.current = now
    if (!before) return
    const fresh: Ghost[] = []
    for (const [id, p] of played) {
      if (!p.winner || before.get(id) === p.winner.name) continue
      const slot = p.players[0]?.name === p.winner.name ? 0 : 1
      const from = L.chip(id, slot)
      const m = p.match
      const champion = !m.next
      const to = champion ? L.champion : L.chip(m.next!.id, m.next!.slot)
      if (reduced) {
        if (champion) onChampion?.(p.winner, null)
        continue
      }
      fresh.push({ key: champion ? "champion" : `${m.next!.id}:${m.next!.slot}`, entrant: p.winner, from, to, champion })
    }
    if (!fresh.length) return
    setGhosts((g) => [...g.filter((x) => !fresh.some((f) => f.key === x.key)), ...fresh])
    setArriving((a) => new Set([...a, ...fresh.map((f) => f.key)]))
  }, [played, L, reduced, onChampion])

  const landed = (g: Ghost) => {
    setGhosts((all) => all.filter((x) => x !== g))
    setArriving((a) => {
      const n = new Set(a)
      n.delete(g.key)
      return n
    })
    if (g.champion) {
      setCheer((c) => c + 1)
      requestAnimationFrame(() => onChampion?.(g.entrant, bannerRef.current?.getBoundingClientRect() ?? null))
    }
  }

  const champion = played.get(finalId)?.winner ?? null
  const finalScore = played.get(finalId)?.score
  const height = (width * L.height) / L.width

  return (
    <svg
      viewBox={`0 0 ${L.width} ${L.height}`}
      width={width}
      height={height}
      role="img"
      aria-label={`${bracket.entrants.length} entrant bracket`}
      className="block overflow-visible select-none"
    >
      {L.columns.map((c) => {
        const anchor = c.side === "right" ? "end" : c.side === "center" ? "middle" : "start"
        const x = c.side === "right" ? c.x + CHIP_W : c.side === "center" ? c.x + CHIP_W / 2 : c.x
        if (c.side === "center") {
          const p = L.matchPos.get(finalId)!
          return (
            <text key={`label-${c.side}-${c.round}`} className="round-label" x={x} y={p.y + MATCH_H / 2 + 24} textAnchor={anchor}>
              {roundName(c.round, bracket.rounds).toUpperCase()}
            </text>
          )
        }
        return (
          <text key={`label-${c.side}-${c.round}`} className="round-label" x={x} y={14} textAnchor={anchor}>
            {roundName(c.round, bracket.rounds).toUpperCase()}
          </text>
        )
      })}

      <g>
        {L.connectors.map((c) => {
          const bye = c.id.startsWith("bye:")
          const live = !bye && !!played.get(c.from)?.winner
          const m = bracket.byId.get(c.from)
          const delay = bye ? 300 : live ? 0 : ((m?.round ?? 1) - 1) * 90 + (m?.index ?? 0) * 10
          return (
            <path
              key={`${c.id}-${live ? "live" : "idle"}`}
              d={c.d}
              pathLength={1}
              className="connector"
              data-live={live}
              data-bye={bye}
              style={{ "--delay": `${delay}ms`, "--draw-ms": live ? `${SPRING.slide.ms}ms` : "520ms" } as CSSProperties}
            />
          )
        })}
        <path
          key={`final-${champion ? "live" : "idle"}`}
          d={L.finalLink}
          pathLength={1}
          className="connector"
          data-live={!!champion}
          style={{ "--delay": champion ? "0ms" : `${(bracket.rounds - 1) * 90 + 60}ms` } as CSSProperties}
        />
      </g>

      {L.byeGhosts.map((g) => (
        <g key={`bye-${g.entrant.seed}`} className="chip" data-state="lost" transform={`translate(${g.x} ${g.y})`} style={teamStyle(g.entrant.color)}>
          <rect className="chip-body" width={CHIP_W} height={CHIP_H} rx={5} strokeDasharray="3 3" />
          <path className="chip-bar" d={`M5 0V${CHIP_H}A5 5 0 0 1 0 ${CHIP_H - 5}V5A5 5 0 0 1 5 0Z`} />
          <text className="chip-seed" x={24} y={20} textAnchor="end">
            {g.entrant.seed}
          </text>
          <text className="chip-name" x={30} y={22}>
            {fit(g.entrant.name, CHIP_W - 76)}
          </text>
          <text className="chip-score" x={CHIP_W - 10} y={21} textAnchor="end">
            {copy.bye}
          </text>
        </g>
      ))}

      {bracket.matches.map((m) => {
        const p = played.get(m.id)!
        const pos = L.matchPos.get(m.id)!
        const delay = (m.round - 1) * 90 + m.index * 10
        return (
          <g
            key={m.id}
            data-match={m.id}
            className="animate-in fade-in fill-mode-both duration-500"
            style={{ animationDelay: `${delay}ms` }}
          >
            {[0, 1].map((slot) => {
              const e = p.players[slot]
              const key = `${m.id}:${slot}`
              const hidden = arriving.has(key)
              const state = !e ? "empty" : p.winner ? (p.winner.name === e.name ? "won" : "lost") : "open"
              const c = L.chip(m.id, slot as 0 | 1)
              return (
                <Chip
                  key={slot}
                  entrant={hidden ? null : e}
                  x={c.x}
                  y={c.y}
                  state={hidden ? "empty" : state}
                  upset={!hidden && p.upset && state === "lost"}
                  score={p.winner && e ? scoreFor(p.score, slot, p.players[0]?.name === p.winner.name ? 0 : 1) : undefined}
                />
              )
            })}
            {p.upset && p.winner && (
              <g transform={`translate(${pos.x + CHIP_W - 50} ${p.players[0]?.name === p.winner.name ? L.chip(m.id, 0).y - 10 : L.chip(m.id, 1).y + CHIP_H - 5})`} className="animate-in zoom-in-75 fade-in duration-300">
                <rect className="upset-tag" width={44} height={15} rx={7.5} />
                <text className="upset-tag-text" x={22} y={10.5} textAnchor="middle">
                  {copy.upset.toUpperCase()}
                </text>
              </g>
            )}
          </g>
        )
      })}

      <g className="champion-slot">
        {champion && !arriving.has("champion") ? (
          <ChampionChip entrant={champion} x={L.champion.x} y={L.champion.y} />
        ) : (
          <g className="chip" data-state="empty" transform={`translate(${L.champion.x} ${L.champion.y})`}>
            <rect className="chip-body" width={CHAMP_W} height={CHAMP_H} rx={8} />
            <text className="round-label" x={CHAMP_W / 2} y={CHAMP_H / 2 + 5} textAnchor="middle">
              {copy.champion.toUpperCase()}
            </text>
          </g>
        )}
      </g>

      <foreignObject x={L.banner.x} y={L.banner.y} width={L.banner.w} height={L.banner.h}>
        <div ref={bannerRef} className="flex h-full items-end justify-center">
          {champion && !arriving.has("champion") && (
            <ChampionBanner key={`${champion.name}-${cheer}`} name={champion.name} label={copy.champion} score={finalScore} animate={cheer > 0 && !reduced} color={champion.color} />
          )}
        </div>
      </foreignObject>

      {ghosts.map((g) => (
        <GhostChip key={g.key + g.entrant.name} ghost={g} onDone={() => landed(g)} />
      ))}
    </svg>
  )
}

/** A score is written winner first, "64-58"; each chip shows its own number. Any other text shows on the winner's chip. */
export function scoreFor(score: string | undefined, slot: number, winnerSlot: number): string | undefined {
  if (!score) return undefined
  const parts = score.split(/\s*[-–—:]\s*/).map((x) => x.trim())
  if (parts.length === 2 && parts.every((x) => x.length > 0 && x.length <= 4)) return slot === winnerSlot ? parts[0] : parts[1]
  return slot === winnerSlot ? truncate(score, 8) : undefined
}

function Chip({ entrant, x, y, state, upset, score }: { entrant: Entrant | null; x: number; y: number; state: string; upset: boolean; score?: string }) {
  return (
    <g className="chip" data-state={state} data-upset={upset} transform={`translate(${x} ${y})`} style={entrant ? teamStyle(entrant.color) : undefined}>
      <rect className="chip-body" width={CHIP_W} height={CHIP_H} rx={5} />
      <rect className="chip-flash" width={CHIP_W} height={CHIP_H} rx={5} />
      {entrant && (
        <>
          <path className="chip-bar" d={`M5 0V${CHIP_H}A5 5 0 0 1 0 ${CHIP_H - 5}V5A5 5 0 0 1 5 0Z`} />
          <text className="chip-seed" x={24} y={20} textAnchor="end">
            {entrant.seed}
          </text>
          <text className="chip-name" x={30} y={22}>
            {fit(entrant.name, CHIP_W - (score ? 66 : 40), state === "won" ? 750 : 600)}
          </text>
          {score && (
            <text className="chip-score" x={CHIP_W - 10} y={21} textAnchor="end">
              {score}
            </text>
          )}
          {upset && <line className="chip-strike" x1={28} x2={CHIP_W - 40} y1={CHIP_H / 2} y2={CHIP_H / 2} />}
        </>
      )}
    </g>
  )
}

function ChampionChip({ entrant, x, y }: { entrant: Entrant; x: number; y: number }) {
  return (
    <g className="chip" data-state="won" transform={`translate(${x} ${y})`} style={teamStyle(entrant.color)}>
      <rect className="chip-body" width={CHAMP_W} height={CHAMP_H} rx={8} />
      <path className="chip-bar" d={`M8 0V${CHAMP_H}A8 8 0 0 1 0 ${CHAMP_H - 8}V8A8 8 0 0 1 8 0Z`} />
      <text className="chip-seed" x={30} y={25} textAnchor="end">
        {entrant.seed}
      </text>
      <text className="chip-name" x={38} y={27}>
        {fit(entrant.name, CHAMP_W - 52, 800, 20)}
      </text>
    </g>
  )
}

function GhostChip({ ghost, onDone }: { ghost: Ghost; onDone: () => void }) {
  const ref = useRef<SVGGElement>(null)
  const done = useRef(onDone)
  useLayoutEffect(() => {
    done.current = onDone
  })
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const { from: a, to: b, champion } = ghost
    const dx = champion ? (CHAMP_W - CHIP_W) / 2 : 0
    const mx = (a.x + b.x + dx) / 2
    const frames = champion
      ? [
          { transform: `translate(${a.x}px, ${a.y}px) scale(1)` },
          { transform: `translate(${b.x + dx}px, ${b.y + (CHAMP_H - CHIP_H) / 2}px) scale(1.18)` },
        ]
      : [
          { transform: `translate(${a.x}px, ${a.y}px)` },
          { transform: `translate(${mx}px, ${a.y}px)`, offset: 0.42 },
          { transform: `translate(${mx}px, ${b.y}px)`, offset: 0.62 },
          { transform: `translate(${b.x}px, ${b.y}px)` },
        ]
    const anim = el.animate(frames, { duration: SPRING.slide.ms + 40, easing: SPRING.slide.easing, fill: "forwards" })
    anim.onfinish = () => done.current()
    return () => anim.cancel()
  }, [ghost])
  return (
    <g ref={ref} className="chip" data-state="won" style={teamStyle(ghost.entrant.color)}>
      <rect className="chip-body" width={CHIP_W} height={CHIP_H} rx={5} />
      <path className="chip-bar" d={`M5 0V${CHIP_H}A5 5 0 0 1 0 ${CHIP_H - 5}V5A5 5 0 0 1 5 0Z`} />
      <text className="chip-seed" x={24} y={20} textAnchor="end">
        {ghost.entrant.seed}
      </text>
      <text className="chip-name" x={30} y={22}>
        {fit(ghost.entrant.name, CHIP_W - 40, 750)}
      </text>
    </g>
  )
}
