import { useCallback, useEffect, useRef, useState } from "react"
import { BikeIcon, FootprintsIcon, ImageIcon, LocateFixedIcon, MountainIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { ColorKey } from "@/components/ColorKey"
import { FlatMap } from "@/components/FlatMap"
import { chartTitle, ProfileChart, type Metric } from "@/components/ProfileChart"
import { ReplayControls } from "@/components/ReplayControls"
import { ReplayMap } from "@/components/ReplayMap"
import { RouteOverview } from "@/components/RouteOverview"
import { SplitsTable } from "@/components/SplitsTable"
import { StatRoll } from "@/components/StatRoll"
import { Telemetry } from "@/components/Telemetry"
import { TopBar } from "@/components/TopBar"
import { defaultRate, type ReplayClock } from "@/lib/clock"
import { config } from "@/lib/config"
import { hasWebGL, reducedMotion, weakDevice } from "@/lib/device"
import { distanceUnit, distanceValue, formatDate, formatDuration, formatPace, formatTimeOfDay, formatWhole, heightUnit, heightValue, paceLabel, paceName, sportName } from "@/lib/format"
import { href, type Route } from "@/lib/route"
import { effectiveColorBy, totalTime } from "@/lib/track"
import type { ColorBy, Sport, Track } from "@/lib/types"
import { cn } from "@/lib/utils"

const ICON: Record<Sport, typeof BikeIcon> = { run: FootprintsIcon, ride: BikeIcon, hike: MountainIcon }
const METRICS: Metric[] = ["elevation", "pace", "heart"]
const webgl = hasWebGL()

interface ReplayScreenProps {
  track: Track
  clock: ReplayClock
  route: Route
}

function Stat({ label, value, unit, format, delay }: { label: string; value: number | null; unit?: string; format: (n: number) => string; delay: number }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="font-display text-[2.5rem] leading-none font-bold short:text-3xl">
        {value == null ? "–" : <StatRoll value={value} format={format} delay={delay} />}
        {unit && value != null ? <span className="ml-1 font-sans text-sm font-normal text-muted-foreground">{unit}</span> : null}
      </dd>
    </div>
  )
}

const twoPlaces = (n: number) => n.toFixed(2)
const clockTime = (n: number) => formatDuration(n)

function Stats({ track }: { track: Track }) {
  const units = config.units
  const s = track.summary
  const paceFormat = useCallback((n: number) => formatPace(n, track.sport, units), [track.sport, units])
  return (
    <dl className="grid grid-cols-3 gap-x-4 gap-y-5 lg:grid-cols-2 2xl:grid-cols-3">
      <Stat label="Distance" value={distanceValue(s.distance, units)} unit={distanceUnit(units)} format={twoPlaces} delay={0} />
      <Stat label="Moving time" value={s.moving} format={clockTime} delay={80} />
      <Stat label="Climb" value={heightValue(s.climb, units)} unit={heightUnit(units)} format={formatWhole} delay={160} />
      <Stat label={`Average ${paceName(track.sport).toLowerCase()}`} value={s.avgSpeed} unit={paceLabel(track.sport, units)} format={paceFormat} delay={240} />
      <Stat label="Average heart rate" value={s.avgHr} unit="bpm" format={formatWhole} delay={320} />
      <Stat label="High point" value={s.maxEle == null ? null : heightValue(s.maxEle, units)} unit={heightUnit(units)} format={formatWhole} delay={400} />
    </dl>
  )
}

function Title({ track, className }: { track: Track; className?: string }) {
  const Icon = ICON[track.sport]
  return (
    <div className={cn("flex min-w-0 flex-col gap-1.5", className)}>
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Badge variant="secondary" className="gap-1.5">
          <Icon aria-hidden="true" />
          {sportName(track.sport)}
        </Badge>
        <span className="truncate">
          {formatDate(track.start)}
          {track.start ? `, ${formatTimeOfDay(track.start)}` : ""}
        </span>
      </div>
      <h1 className="font-display text-[2.75rem] leading-[0.95] font-bold 2xl:text-6xl">{track.name}</h1>
    </div>
  )
}

/** A swipeable strip on a phone, three charts side by side on a wide screen. */
function ChartStrip({ track, clock }: { track: Track; clock: ReplayClock }) {
  const strip = useRef<HTMLDivElement>(null)
  const [shown, setShown] = useState(0)
  useEffect(() => {
    const el = strip.current
    if (!el) return
    const onScroll = () => setShown(Math.round(el.scrollLeft / Math.max(1, el.clientWidth)))
    el.addEventListener("scroll", onScroll, { passive: true })
    return () => el.removeEventListener("scroll", onScroll)
  }, [])
  const go = (i: number) => strip.current?.scrollTo({ left: i * strip.current.clientWidth, behavior: reducedMotion.matches ? "auto" : "smooth" })
  return (
    <section aria-label="Charts" className="flex min-h-0 flex-1 flex-col gap-2">
      <div className="flex items-center gap-1 lg:hidden" role="tablist" aria-label="Chart">
        {METRICS.map((metric, i) => (
          <button
            key={metric}
            role="tab"
            aria-selected={shown === i}
            onClick={() => go(i)}
            className={cn(
              "h-9 rounded-full px-3 text-sm font-medium text-muted-foreground transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring",
              shown === i && "bg-muted text-foreground",
            )}
          >
            {chartTitle(metric, track)}
          </button>
        ))}
      </div>
      <div
        ref={strip}
        className="chart-strip flex h-40 min-h-0 gap-8 snap-x snap-mandatory overflow-x-auto overscroll-x-contain lg:grid lg:h-auto lg:flex-1 lg:grid-cols-[1.4fr_1fr_1fr] lg:gap-6 lg:overflow-visible short:h-36"
      >
        {METRICS.map((metric) => (
          <ProfileChart key={metric} track={track} metric={metric} units={config.units} clock={clock} className="w-full shrink-0 snap-start px-2 lg:w-auto lg:px-0" />
        ))}
      </div>
    </section>
  )
}

export function ReplayScreen({ track, clock, route }: ReplayScreenProps) {
  const [colorBy, setColorBy] = useState<ColorBy>(() => effectiveColorBy(track, config.colorBy))
  const [follow, setFollow] = useState(true)
  const [lite, setLite] = useState(() => (webgl && weakDevice()))
  const [shownFor, setShownFor] = useState(track.id)
  if (shownFor !== track.id) {
    setShownFor(track.id)
    setColorBy(effectiveColorBy(track, config.colorBy))
    setFollow(true)
  }

  // A new activity resets the clock and starts the replay, unless the device asks for less motion.
  useEffect(() => {
    clock.pause()
    clock.setDuration(totalTime(track))
    clock.setRate(defaultRate(totalTime(track)))
    clock.seek(0)
    if (!reducedMotion.matches) clock.play()
  }, [track, clock])

  const onUserMove = useCallback(() => setFollow(false), [])
  const onSlow = useCallback(() => setLite(true), [])

  return (
    <div className="flex min-h-dvh flex-col lg:grid lg:h-dvh lg:min-h-0 lg:grid-cols-[minmax(0,1fr)_400px] lg:grid-rows-[minmax(0,1fr)_auto] 2xl:grid-cols-[minmax(0,1fr)_460px] short:grid short:h-dvh short:min-h-0 short:grid-cols-[minmax(0,1fr)_minmax(340px,46%)] short:grid-rows-1">
      <section className="relative h-[58svh] min-h-[360px] overflow-hidden bg-map lg:col-start-1 lg:row-start-1 lg:h-auto lg:min-h-0 short:h-auto short:min-h-0" aria-label="Replay map">
        {webgl ? (
          <ReplayMap track={track} clock={clock} colorBy={colorBy} labels={config.labels} follow={follow} lite={lite} onUserMove={onUserMove} onSlow={onSlow} />
        ) : (
          <FlatMap track={track} clock={clock} colorBy={colorBy} />
        )}
        <div className="map-scrim-top pointer-events-none absolute inset-x-0 top-0 h-36" aria-hidden="true" />
        <TopBar
          route={route}
          activityId={track.id}
          athlete={config.athlete}
          overMap
          className="absolute inset-x-0 top-0 px-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:px-5 sm:pt-5"
        />
        <div data-map-hud className="absolute right-12 bottom-3 left-3 flex items-end gap-3 sm:right-5 sm:bottom-5 sm:left-5 lg:bottom-9 short:right-14">
          <div className="flex min-w-0 flex-col gap-2">
            <Title track={track} className="glass rounded-xl border px-3.5 py-2.5 shadow-sm lg:hidden short:hidden [&_h1]:text-3xl" />
            <Telemetry track={track} clock={clock} units={config.units} className="max-w-full" />
          </div>
          {!follow && webgl && !reducedMotion.matches ? (
            <Button variant="secondary" className="glass ml-auto h-11 border px-4 shadow-sm" onClick={() => setFollow(true)}>
              <LocateFixedIcon data-icon="inline-start" />
              Follow
            </Button>
          ) : null}
        </div>
      </section>

      <section
        className="flex flex-col gap-4 border-t bg-background px-4 py-4 lg:col-start-1 lg:row-start-2 lg:h-[276px] lg:px-6 2xl:h-[316px] short:hidden"
        aria-label="Replay"
      >
        <ReplayControls clock={clock} />
        <ChartStrip track={track} clock={clock} />
      </section>

      <aside className="flex flex-col gap-7 border-t bg-background px-4 pt-6 pb-[max(2rem,env(safe-area-inset-bottom))] lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:overflow-y-auto lg:border-t-0 lg:border-l lg:px-7 lg:pt-7 short:overflow-y-auto short:border-t-0 short:border-l short:pt-[max(1rem,env(safe-area-inset-top))]">
        <Title track={track} className="hidden lg:flex short:flex" />
        <div className="hidden flex-col gap-4 short:flex">
          <ReplayControls clock={clock} />
          <ChartStrip track={track} clock={clock} />
        </div>
        <Stats track={track} />
        <Separator />
        <ColorKey track={track} units={config.units} colorBy={colorBy} onChange={setColorBy} />
        <Separator />
        <section className="flex flex-col gap-3" aria-labelledby="splits-title">
          <h2 id="splits-title" className="text-sm font-medium">
            Splits
          </h2>
          <SplitsTable track={track} clock={clock} units={config.units} />
        </section>
        <RouteOverview track={track} clock={clock} units={config.units} className="hidden roomy:flex roomy:flex-1 roomy:min-h-40" />
        <Button variant="outline" size="lg" className="h-11" render={<a href={href({ screen: "poster", id: track.id })} />} nativeButton={false}>
          <ImageIcon data-icon="inline-start" />
          Make a poster of this route
        </Button>
      </aside>
    </div>
  )
}
