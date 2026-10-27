import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import { DownloadIcon, ExpandIcon, MaximizeIcon, RotateCcwIcon, UploadIcon } from "lucide-react"
import { buildBracket, cleanPicks, cleanResults, play, standings, type Entrant, type Picks, type Results } from "@/lib/bracket"
import { readConfig } from "@/lib/config"
import { layout } from "@/lib/layout"
import { download, fromExport, load, save, toExport } from "@/lib/store"
import { burst } from "@/lib/confetti"
import { selftest } from "@/lib/selftest"
import { useMedia, useReducedMotion, useScheme } from "@/lib/hooks"
import { BracketSvg } from "@/components/bracket-svg"
import { RoundsView } from "@/components/rounds-view"
import { PoolPills, PoolStrip, PoolTable } from "@/components/leaderboard"
import { PicksScreen } from "@/components/picks-screen"
import { ResultsScreen } from "@/components/results-screen"
import { BigScreen } from "@/components/big-screen"
import { ZoomSheet } from "@/components/zoom-sheet"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

const config = readConfig()
const bracket = buildBracket(config.entrants, config.colors)
const params = new URLSearchParams(location.search)

// The replay: the lines start drawing, then each result lands in bracket order, quicker in the first round, with a
// beat between rounds and a longer one before the final. Every slide has landed and the champion is crowned by
// about 1.4 s, so a look at the page two seconds after it opens finds every chip in its slot and the banner up.
function schedule(order: { round: number }[], finalRound: number): number[] {
  const times: number[] = []
  let t = 150
  let round = order[0]?.round ?? 1
  for (const m of order) {
    if (m.round !== round) {
      t += m.round === finalRound ? 70 : 50
      round = m.round
    }
    times.push(t)
    t += m.round === 1 ? 30 : 50
  }
  return times
}

function useBox<T extends HTMLElement>(): [React.RefObject<T | null>, { w: number; h: number }] {
  const ref = useRef<T>(null)
  const [box, setBox] = useState({ w: 0, h: 0 })
  useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    const measure = () => setBox({ w: el.clientWidth, h: el.clientHeight })
    measure()
    const ro = new ResizeObserver(measure)
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, box]
}

export default function App() {
  useScheme()
  const reduced = useReducedMotion()
  const wide = useMedia("(min-width: 768px)")
  const copy = config.copy

  const [state, setState] = useState(() => load(bracket, config))
  const { results, picks } = state
  const [tab, setTab] = useState("bracket")
  const [person, setPerson] = useState(0)
  const [big, setBig] = useState(params.get("tv") === "1")
  const [whole, setWhole] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [test, setTest] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  // How many of the results are on the sheet; null once the replay is over.
  const [revealed, setRevealed] = useState<number | null>(reduced ? null : 0)
  const [run, setRun] = useState(0)
  const order = useMemo(() => bracket.matches.filter((m) => results[m.id]), [results])

  useEffect(() => {
    if (revealed === null) return
    if (revealed !== 0) return
    const times = schedule(order, bracket.rounds)
    const timers = times.map((t, i) => window.setTimeout(() => setRevealed((r) => (r === null ? null : Math.max(r, i + 1))), t))
    timers.push(window.setTimeout(() => setRevealed(null), (times[times.length - 1] ?? 0) + 2400))
    return () => timers.forEach(clearTimeout)
    // The schedule is set once per replay run.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [run])

  const shown: Results = useMemo(() => {
    if (revealed === null) return results
    const out: Results = {}
    order.slice(0, revealed).forEach((m) => (out[m.id] = results[m.id]))
    return out
  }, [results, order, revealed])

  const played = useMemo(() => play(bracket, shown), [shown])
  const allPlayed = useMemo(() => play(bracket, results), [results])
  const table = useMemo(() => standings(bracket, played, config.people, picks), [played, picks])

  useEffect(() => {
    document.title = config.title
  }, [])

  const first = useRef(true)
  useEffect(() => {
    if (first.current) {
      first.current = false
      return
    }
    save(config, results, picks)
  }, [results, picks])

  useEffect(() => {
    if (!notice) return
    const t = window.setTimeout(() => setNotice(null), 4000)
    return () => clearTimeout(t)
  }, [notice])

  useEffect(() => {
    if (params.get("selftest") !== "1") return
    const t = window.setTimeout(() => {
      const problems = selftest(bracket, config, results, picks)
      const line = problems.length ? problems.join("; ") : "round trip ok"
      console.log(line)
      setTest(line)
    }, 200)
    return () => clearTimeout(t)
    // Runs once, on the state the page loaded with.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const replay = () => {
    setRevealed(reduced ? null : 0)
    setRun((r) => r + 1)
  }

  const onChampion = useCallback(
    (entrant: Entrant, at: DOMRect | null) => {
      if (reduced || !at) return
      const css = getComputedStyle(document.documentElement)
      const theme = ["--win", "--banner-accent", "--upset", "--foreground"].map((v) => css.getPropertyValue(v).trim()).filter(Boolean)
      const colors = [entrant.color, entrant.color, ...theme]
      const y = at.top + at.height * 0.7
      burst({ x: at.left + 10, y }, colors, 110, -Math.PI * 0.68)
      burst({ x: at.right - 10, y }, colors, 110, -Math.PI * 0.32)
    },
    [reduced],
  )

  const setResult = (match: string, winner: string | null, score?: string) => {
    setRevealed(null)
    setState((s) => {
      const next = { ...s.results }
      if (winner) next[match] = { winner, ...(score ? { score } : {}) }
      else delete next[match]
      return { ...s, results: cleanResults(bracket, next) }
    })
  }

  const setPick = (who: string, match: string, name: string) => {
    setState((s) => {
      const mine = { ...(s.picks[who] ?? {}), [match]: name }
      const next: Picks = { ...s.picks, [who]: cleanPicks(bracket, mine) }
      return { ...s, picks: next }
    })
  }

  const importFile = async (file: File | undefined) => {
    if (!file) return
    const back = fromExport(bracket, config, await file.text())
    if (!back) {
      setNotice(copy.importFailed)
      return
    }
    setState(back)
    setNotice(copy.imported)
    replay()
  }

  // A phone button is a 44 px square, the size of a thumb.
  const tap = wide ? undefined : "size-11 [&_svg:not([class*='size-'])]:size-5"
  const actions = (
    <div className="flex items-center gap-1.5">
      <Button variant="outline" size={wide ? "default" : "icon-lg"} className={tap} onClick={replay} aria-label={copy.replay}>
        <RotateCcwIcon />
        {wide && copy.replay}
      </Button>
      {!wide && (
        <Button variant="outline" size="icon-lg" className={tap} onClick={() => setWhole(true)} aria-label={copy.wholeBracket}>
          <ExpandIcon />
        </Button>
      )}
      {wide && (
        <Button variant="outline" onClick={() => setBig(true)}>
          <MaximizeIcon />
          {copy.bigScreen}
        </Button>
      )}
      <Button variant="outline" size={wide ? "default" : "icon-lg"} className={tap} onClick={() => download(toExport(bracket, config, results, picks))} aria-label={copy.export}>
        <DownloadIcon />
        {wide && copy.export}
      </Button>
      <Button variant="outline" size={wide ? "default" : "icon-lg"} className={tap} onClick={() => fileInput.current?.click()} aria-label={copy.import}>
        <UploadIcon />
        {wide && copy.import}
      </Button>
      <input
        ref={fileInput}
        type="file"
        accept="application/json,.json"
        className="hidden"
        onChange={(e) => {
          void importFile(e.target.files?.[0])
          e.target.value = ""
        }}
      />
    </div>
  )

  const metaParts = [
    `${bracket.entrants.length} ${bracket.entrants.length === 1 ? "entrant" : "entrants"}`,
    `${bracket.matches.length} matches${bracket.byes.length ? ` · ${bracket.byes.length} ${bracket.byes.length === 1 ? "bye" : "byes"}` : ""}`,
  ]
  const meta = metaParts.join(" · ")

  return (
    <Tabs value={tab} onValueChange={setTab} className="flex h-dvh flex-col gap-0 pt-[env(safe-area-inset-top)]">
      {wide ? (
        <header className="flex items-center gap-6 px-6 pt-5 pb-3">
          <div className="min-w-0 flex-1">
            <h1 className="display truncate text-5xl uppercase">{config.title}</h1>
            <p className="truncate text-sm text-muted-foreground" aria-live="polite">
              {notice ?? test ?? meta}
            </p>
          </div>
          <TabsList className="h-10! px-1">
            {(["bracket", "picks", "results", "pool"] as const).map((t) => (
              <TabsTrigger key={t} value={t} className="px-4 text-[0.95rem]">
                {copy[t]}
              </TabsTrigger>
            ))}
          </TabsList>
          {actions}
        </header>
      ) : (
        <header className="flex flex-col gap-1 px-4 pt-3 pb-2">
          <h1 className="display line-clamp-2 text-[1.85rem] uppercase">{config.title}</h1>
          <div className="flex items-center gap-3">
            <p className="line-clamp-2 min-w-0 flex-1 text-sm leading-snug text-muted-foreground" aria-live="polite">
              {notice ?? test ?? metaParts.map((part) => (
                <span key={part} className="block">
                  {part}
                </span>
              ))}
            </p>
            {actions}
          </div>
        </header>
      )}
      {!wide && (
        <TabsList variant="line" className="mx-4 mb-2 w-auto! justify-stretch border-b border-border">
          {(["bracket", "picks", "results", "pool"] as const).map((t) => (
            <TabsTrigger key={t} value={t} className="text-[0.95rem]">
              {copy[t]}
            </TabsTrigger>
          ))}
        </TabsList>
      )}

      <TabsContent value="bracket" className="flex min-h-0 flex-1 flex-col">
        {wide ? (
          <DesktopBracket key={run} played={played} reduced={reduced} onChampion={onChampion} />
        ) : (
          <div className="flex min-h-0 flex-1 flex-col gap-2 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
            <RoundsView bracket={bracket} played={played} copy={copy} reduced={reduced} />
            <PoolPills standings={table} bracket={bracket} copy={copy} reduced={reduced} />
          </div>
        )}
        {wide && (
          <div className="px-6 pt-2 pb-5">
            <PoolStrip standings={table} bracket={bracket} copy={copy} reduced={reduced} />
          </div>
        )}
      </TabsContent>
      <TabsContent value="picks" className="min-h-0 flex-1 overflow-y-auto px-4 pb-8 md:px-6">
        <PicksScreen bracket={bracket} played={allPlayed} people={config.people} picks={picks} person={person} copy={copy} onPerson={setPerson} onPick={setPick} />
      </TabsContent>
      <TabsContent value="results" className="min-h-0 flex-1 overflow-y-auto px-4 pb-8 md:px-6">
        <ResultsScreen bracket={bracket} played={allPlayed} results={results} copy={copy} onResult={setResult} />
      </TabsContent>
      <TabsContent value="pool" className="min-h-0 flex-1 overflow-y-auto px-4 pb-8 md:px-6">
        <div className="surface rounded-xl p-2 md:p-4">
          <PoolTable standings={table} bracket={bracket} copy={copy} reduced={reduced} />
        </div>
      </TabsContent>

      <Dialog open={whole} onOpenChange={setWhole}>
        <DialogContent className="flex max-h-[90dvh] max-w-[calc(100%-1rem)] flex-col gap-3 p-3 sm:max-w-[calc(100%-2rem)]">
          <DialogTitle className="display pr-10 text-2xl uppercase">{copy.wholeBracket}</DialogTitle>
          <ZoomSheet base={window.innerWidth - 40}>
            {(w) => <BracketSvg bracket={bracket} layout={layout(bracket)} played={played} copy={copy} reduced={reduced} width={w} />}
          </ZoomSheet>
        </DialogContent>
      </Dialog>

      {big && (
        <BigScreenBracket
          played={played}
          reduced={reduced}
          onChampion={onChampion}
          onClose={() => setBig(false)}
          foot={<PoolStrip standings={table} bracket={bracket} copy={copy} reduced={reduced} />}
        />
      )}
    </Tabs>
  )
}

type SheetProps = { played: ReturnType<typeof play>; reduced: boolean; onChampion: (e: Entrant, at: DOMRect | null) => void }

const base = layout(bracket)

/** The desktop's sheet: as wide as the window, and stretched taller to fill the height it has. */
function DesktopBracket({ played, reduced, onChampion }: SheetProps) {
  const [ref, box] = useBox<HTMLDivElement>()
  const inner = box.w - 48
  const width = Math.max(inner, base.width * 0.7)
  const minH = inner > 0 ? Math.max(540, Math.round((base.width * box.h) / width)) : 540
  const L = useMemo(() => layout(bracket, minH), [minH])
  return (
    <div ref={ref} className="min-h-0 flex-1 overflow-auto px-6">
      {inner > 0 && <BracketSvg bracket={bracket} layout={L} played={played} copy={config.copy} reduced={reduced} width={width - 1} onChampion={onChampion} />}
    </div>
  )
}

function BigScreenBracket({ played, reduced, onChampion, onClose, foot }: SheetProps & { onClose: () => void; foot: React.ReactNode }) {
  const aspect = Math.max(540, Math.round((base.width * (window.innerHeight - 220)) / Math.max(1, window.innerWidth - 48)))
  const L = useMemo(() => layout(bracket, aspect), [aspect])
  return (
    <BigScreen title={config.title} leave={config.copy.leaveBigScreen} ratio={L.height / L.width} onClose={onClose} foot={foot}>
      {(w) => <BracketSvg bracket={bracket} layout={L} played={played} copy={config.copy} reduced={reduced} width={w} onChampion={onChampion} />}
    </BigScreen>
  )
}
