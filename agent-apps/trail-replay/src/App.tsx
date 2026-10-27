import { useEffect, useMemo, useState } from "react"
import { Skeleton } from "@/components/ui/skeleton"
import { Wordmark } from "@/components/TopBar"
import { ReplayClock } from "@/lib/clock"
import { config, storageKey } from "@/lib/config"
import { loadIndex, loadTrack } from "@/lib/data"
import { reducedMotion } from "@/lib/device"
import { useRoute } from "@/lib/route"
import type { ActivityIndex, Track } from "@/lib/types"
import { ActivitiesScreen } from "@/screens/ActivitiesScreen"
import { PosterScreen } from "@/screens/PosterScreen"
import { ReplayScreen } from "@/screens/ReplayScreen"

const LAST = storageKey("last-activity")

function readLast() {
  try {
    return window.localStorage.getItem(LAST)
  } catch {
    return null
  }
}

function Empty({ text }: { text: string }) {
  return (
    <main className="flex min-h-dvh flex-col gap-10 px-6 pt-[max(1.5rem,env(safe-area-inset-top))]">
      <Wordmark athlete={config.athlete} />
      <div className="mx-auto flex max-w-md flex-1 flex-col items-center justify-center gap-3 pb-24 text-center">
        <h1 className="font-display text-4xl font-bold">No activities yet</h1>
        <p className="text-muted-foreground">{text}</p>
      </div>
    </main>
  )
}

function Loading() {
  return (
    <div className="flex min-h-dvh flex-col lg:grid lg:h-dvh lg:grid-cols-[minmax(0,1fr)_400px]" aria-busy="true" aria-label="Loading the activity">
      <div className="h-[58svh] bg-map lg:h-auto" />
      <div className="flex flex-col gap-4 p-6">
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-12 w-4/5" />
        <Skeleton className="h-32 w-full" />
      </div>
    </div>
  )
}

export default function App() {
  const route = useRoute()
  const clock = useMemo(() => new ReplayClock(), [])
  const [index, setIndex] = useState<ActivityIndex | null>(null)
  const [failed, setFailed] = useState(false)
  const [track, setTrack] = useState<Track | null>(null)

  useEffect(() => {
    loadIndex().then(setIndex, () => setFailed(true))
  }, [])

  const wantedId = route.screen === "activities" ? null : route.id
  const known = index?.activities ?? []
  const lastId = readLast()
  const id =
    (wantedId && known.some((a) => a.id === wantedId) && wantedId) ||
    (lastId && known.some((a) => a.id === lastId) && lastId) ||
    known[0]?.id ||
    null

  useEffect(() => {
    if (!id) return
    let current = true
    loadTrack(id).then(
      (next) => {
        if (!current) return
        setTrack(next)
        try {
          window.localStorage.setItem(LAST, next.id)
        } catch {
          // A browser that keeps nothing still replays.
        }
      },
      () => current && setFailed(true),
    )
    return () => {
      current = false
    }
  }, [id])

  useEffect(() => {
    if (route.screen !== "replay") clock.pause()
    else if (track && clock.t < clock.duration && !reducedMotion.matches) clock.play()
  }, [route.screen, clock, track])

  useEffect(() => {
    const names = { replay: "Replay", activities: "Activities", poster: "Poster" }
    document.title = track && route.screen !== "activities" ? `${track.name}: ${names[route.screen]}, Trail Replay` : "Trail Replay"
  }, [track, route.screen])

  if (failed) return <Empty text="Add GPX or TCX files from Strava, Garmin Connect, or Apple Fitness to the activities folder, and they show up here." />
  if (!index) return <Loading />
  if (known.length === 0) return <Empty text="Add GPX or TCX files from Strava, Garmin Connect, or Apple Fitness to the activities folder, and they show up here." />
  if (route.screen === "activities") return <ActivitiesScreen index={index} route={route} lastId={id} />
  if (!track || track.id !== id) return <Loading />
  if (route.screen === "poster") return <PosterScreen track={track} route={route} />
  return <ReplayScreen track={track} clock={clock} route={route} />
}
