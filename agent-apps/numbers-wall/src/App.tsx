import { useMemo, useState } from "react"
import { MonitorIcon, XIcon } from "lucide-react"
import { cn } from "cn"

import { Button } from "@/components/ui/button"
import { Kbd } from "@/components/ui/kbd"
import { MetricDetail } from "@/components/metric-detail"
import { Tile } from "@/components/tile"
import { readConfig, type Copy, type Metric } from "@/lib/config"
import { formatRelative } from "@/lib/format"
import { useScheme } from "@/hooks/use-scheme"
import { useTvMode } from "@/hooks/use-tv-mode"

const config = readConfig()
const { copy } = config

const GRID = "grid grid-flow-row-dense grid-cols-1 gap-4 auto-rows-[11rem] sm:grid-cols-2 lg:grid-cols-4"

export default function App() {
  useScheme()
  const [tv, setTv, moved] = useTvMode()
  const [openId, setOpenId] = useState<string | null>(null)
  // The page rolls up once, on the view it opens on; moving between the wall and TV mode keeps every settled figure
  // and finished sparkline, and only the tiles' places change.
  const reveal = !moved

  const entries = useMemo(
    () =>
      config.groups.flatMap((group, g) => group.metrics.map((metric) => ({ metric, group: group.label, groupIndex: g }))),
    [],
  )
  const placeOf = useMemo(() => new Map(entries.map((e, i) => [e.metric.id, { index: i, group: e.groupIndex }])), [entries])
  const open = entries.find((e) => e.metric.id === openId) ?? null

  const tile = (metric: Metric) => {
    const place = placeOf.get(metric.id) ?? { index: 0, group: 0 }
    return (
      <Tile
        key={metric.id}
        metric={metric}
        index={place.index}
        group={place.group}
        entrance={reveal}
        reveal={reveal}
        copy={copy}
        onOpen={setOpenId}
      />
    )
  }

  return (
    <>
      {tv ? <div className="tv-wash" aria-hidden="true" /> : <div className="wall-backdrop" aria-hidden="true" />}
      <svg className="pointer-events-none absolute size-0" aria-hidden="true">
        <defs>
          <linearGradient id="spark-fade-ramp" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopOpacity={0.25} />
            <stop offset="0.1" stopOpacity={1} />
            <stop offset="0.72" stopOpacity={1} />
            <stop offset="1" stopOpacity={0} />
          </linearGradient>
          <mask id="spark-fade" maskContentUnits="objectBoundingBox">
            <rect width="1" height="1" fill="url(#spark-fade-ramp)" />
          </mask>
        </defs>
      </svg>

      {tv ? (
        <main className="relative z-10 h-dvh overflow-y-auto lg:overflow-hidden p-[max(2rem,env(safe-area-inset-top))_max(2rem,env(safe-area-inset-right))_max(2rem,env(safe-area-inset-bottom))_max(2rem,env(safe-area-inset-left))]">
          <h1 className="sr-only">{config.title}</h1>
          <div className={cn(GRID, "lg:h-full lg:auto-rows-[1fr] lg:gap-5")}>{entries.map((e) => tile(e.metric))}</div>
        </main>
      ) : (
        <div className="relative z-10 mx-auto flex min-h-dvh max-w-[86rem] flex-col px-4 pt-[max(1.5rem,env(safe-area-inset-top))] pb-[max(1.5rem,env(safe-area-inset-bottom))] sm:px-8">
          <header className="flex items-center justify-between gap-4 pb-8">
            <div className="min-w-0">
              <h1 className="truncate text-title font-semibold">{config.title}</h1>
            </div>
            <Button variant="outline" size="lg" className="h-11 gap-2 px-3 sm:h-9" onClick={() => setTv(true)}>
              <MonitorIcon data-icon="inline-start" aria-hidden="true" />
              <span className="sr-only sm:not-sr-only">{copy.tvMode}</span>
              <Kbd className="hidden pointer-fine:sm:inline-flex">F</Kbd>
            </Button>
          </header>

          <main className="flex flex-1 flex-col gap-10">
            {entries.length === 0 && (
              <div className="grid flex-1 place-content-center gap-2 text-center">
                <h2 className="text-title font-semibold">{copy.emptyTitle}</h2>
                <p className="text-pretty text-muted-foreground">{copy.emptyText}</p>
              </div>
            )}
            {config.groups.map((group, i) => (
              <section key={group.label} aria-labelledby={`group-${i}`} className="grid gap-4">
                <h2 id={`group-${i}`} className="flex items-center gap-2 text-label font-medium text-muted-foreground">
                  <span data-group={i % 4} className="size-2 rounded-full bg-spark" aria-hidden="true" />
                  {group.label}
                </h2>
                <div className={GRID}>{group.metrics.map(tile)}</div>
              </section>
            ))}
          </main>

          <Footer refreshedAt={config.refreshedAt} copy={copy} />
        </div>
      )}

      {tv && (
        <button
          type="button"
          onClick={() => setTv(false)}
          aria-label={copy.leaveTvMode}
          className="fixed top-[max(0.5rem,env(safe-area-inset-top))] right-[max(0.5rem,env(safe-area-inset-right))] z-20 grid size-11 place-content-center rounded-full bg-background/70 text-muted-foreground opacity-0 transition-opacity duration-150 outline-none hover:opacity-100 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring active:opacity-100"
        >
          <XIcon className="size-5" aria-hidden="true" />
        </button>
      )}

      <MetricDetail metric={open?.metric ?? null} group={open?.group ?? ""} copy={copy} onClose={() => setOpenId(null)} />
    </>
  )
}

function Footer({ refreshedAt, copy }: { refreshedAt?: string; copy: Copy }) {
  const when = refreshedAt ? new Date(refreshedAt) : null
  const valid = when && !Number.isNaN(when.getTime())
  return (
    <footer className="mt-12 flex flex-wrap items-center justify-between gap-3 border-t pt-4 text-xs text-muted-foreground">
      {valid ? (
        <p>
          {copy.refreshed}{" "}
          <time dateTime={refreshedAt} className="figure text-foreground">
            {when.toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}
          </time>
          , {formatRelative(when, new Date())}
        </p>
      ) : (
        <p>{copy.notRefreshed}</p>
      )}
      <p className="hidden pointer-fine:block">{copy.tvHint}</p>
    </footer>
  )
}
