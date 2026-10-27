import { BikeIcon, FootprintsIcon, MountainIcon } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { MiniRoute } from "@/components/MiniRoute"
import { TopBar } from "@/components/TopBar"
import { config } from "@/lib/config"
import { distanceUnit, formatDistance, formatDuration, formatHeight, formatPace, formatShortDate, formatTimeOfDay, heightUnit, paceLabel, sportName } from "@/lib/format"
import { href, type Route } from "@/lib/route"
import type { ActivityIndex, ActivityMeta, Sport } from "@/lib/types"

const ICON: Record<Sport, typeof BikeIcon> = { run: FootprintsIcon, ride: BikeIcon, hike: MountainIcon }

function ActivityCard({ activity, index }: { activity: ActivityMeta; index: number }) {
  const units = config.units
  const s = activity.summary
  const Icon = ICON[activity.sport]
  return (
    <li className="activity-card" data-index={index} ref={(el) => el?.style.setProperty("--i", String(index))}>
      <a
        href={href({ screen: "replay", id: activity.id })}
        className="group flex h-full flex-col overflow-hidden rounded-xl border bg-card text-card-foreground shadow-sm transition-[transform,box-shadow] duration-200 outline-none hover:-translate-y-0.5 hover:shadow-md focus-visible:ring-2 focus-visible:ring-ring active:translate-y-0"
      >
        <div className="relative aspect-[4/3] bg-muted/60 p-6 sm:p-8">
          <MiniRoute points={activity.mini} className="size-full" label={`Route of ${activity.name}`} />
          <Badge variant="secondary" className="absolute top-3 left-3 gap-1.5">
            <Icon aria-hidden="true" />
            {sportName(activity.sport)}
          </Badge>
        </div>
        <div className="flex flex-1 flex-col gap-3 p-4">
          <div>
            <h2 className="font-display text-2xl leading-tight font-bold">{activity.name}</h2>
            <p className="text-sm text-muted-foreground">
              {formatShortDate(activity.start)}
              {activity.start ? `, ${formatTimeOfDay(activity.start)}` : ""}
            </p>
          </div>
          <dl className="mt-auto grid grid-cols-4 gap-2 text-sm tabular-nums">
            <div>
              <dt className="text-xs text-muted-foreground">Distance</dt>
              <dd className="font-medium">
                {formatDistance(s.distance, units, 1)} {distanceUnit(units)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Time</dt>
              <dd className="font-medium">{formatDuration(s.moving)}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">Climb</dt>
              <dd className="font-medium">
                {formatHeight(s.climb, units)} {heightUnit(units)}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-muted-foreground">{activity.sport === "ride" ? "Speed" : "Pace"}</dt>
              <dd className="font-medium">
                {formatPace(s.avgSpeed, activity.sport, units)}
                <span className="text-muted-foreground">{activity.sport === "ride" ? ` ${paceLabel(activity.sport, units)}` : paceLabel(activity.sport, units)}</span>
              </dd>
            </div>
          </dl>
        </div>
      </a>
    </li>
  )
}

export function ActivitiesScreen({ index, route, lastId }: { index: ActivityIndex; route: Route; lastId: string | null }) {
  const total = index.activities.reduce((sum, a) => sum + a.summary.distance, 0)
  const climb = index.activities.reduce((sum, a) => sum + a.summary.climb, 0)
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-[1760px] flex-col gap-8 px-4 pt-[max(1rem,env(safe-area-inset-top))] pb-[max(2rem,env(safe-area-inset-bottom))] sm:px-8">
      <TopBar route={route} activityId={lastId} athlete={config.athlete} />
      <section className="flex flex-col gap-1">
        <h1 className="font-display text-5xl leading-none font-bold sm:text-6xl">Activities</h1>
        <p className="text-muted-foreground tabular-nums">
          {index.activities.length} {index.activities.length === 1 ? "activity" : "activities"}, {formatDistance(total, config.units, 1)} {distanceUnit(config.units)} and{" "}
          {formatHeight(climb, config.units)} {heightUnit(config.units)} of climbing
          {index.sample ? ". Sample activities in Boulder, Colorado." : "."}
        </p>
      </section>
      <ul className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
        {index.activities.map((activity, i) => (
          <ActivityCard key={activity.id} activity={activity} index={i} />
        ))}
      </ul>
    </div>
  )
}
