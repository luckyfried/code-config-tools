import { ImageIcon, ListIcon, MapIcon } from "lucide-react"
import { href, type Route } from "@/lib/route"
import { cn } from "@/lib/utils"

interface TopBarProps {
  route: Route
  activityId: string | null
  athlete: string
  overMap?: boolean
  className?: string
}

const items = [
  { screen: "replay", label: "Replay", icon: MapIcon },
  { screen: "activities", label: "Activities", icon: ListIcon },
  { screen: "poster", label: "Poster", icon: ImageIcon },
] as const

export function Wordmark({ athlete }: { athlete: string }) {
  return (
    <a href="#/activities" className="flex min-w-0 items-center gap-2.5 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring">
      <svg viewBox="0 0 32 32" className="size-8 shrink-0" aria-hidden="true">
        <rect width="32" height="32" rx="8" className="fill-foreground" />
        <path d="M0 21 L7 15 L11 18 L17 9 L22 15 L25 12 L32 19 L32 32 L0 32 Z" className="fill-background opacity-25" />
        <path d="M5 26 C 10 25, 11 20, 14 19 S 17 14, 16 12 S 20 8, 22 11 S 25 14, 27 12" fill="none" className="stroke-comet" strokeWidth="2.6" strokeLinecap="round" />
        <circle cx="27" cy="12" r="2.6" className="fill-background" />
      </svg>
      <span className="flex min-w-0 flex-col leading-none">
        <span className="font-display text-xl font-bold tracking-wide">Trail Replay</span>
        {athlete ? <span className="truncate text-xs text-muted-foreground">{athlete}</span> : null}
      </span>
    </a>
  )
}

/** The app's name and its three screens. Over the map it sits on glass so the terrain shows through. */
export function TopBar({ route, activityId, athlete, overMap, className }: TopBarProps) {
  return (
    <header className={cn("flex items-center gap-3", className)}>
      <div className={cn("flex min-w-0 items-center rounded-xl", overMap && "glass border px-2.5 py-1.5 shadow-sm")}>
        <Wordmark athlete={athlete} />
      </div>
      <nav aria-label="Screens" className={cn("ml-auto flex items-center gap-1 rounded-xl p-1", overMap ? "glass border shadow-sm" : "bg-muted")}>
        {items.map(({ screen, label, icon: Icon }) => {
          const target: Route =
            screen === "activities" ? { screen } : { screen, id: activityId }
          const current = route.screen === screen
          return (
            <a
              key={screen}
              href={href(target)}
              aria-current={current ? "page" : undefined}
              className={cn(
                "flex h-10 items-center gap-2 rounded-lg px-3 text-sm font-medium text-muted-foreground transition-colors outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring",
                current && "bg-background text-foreground shadow-sm",
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              <span className="sr-only sm:not-sr-only short:sr-only">{label}</span>
            </a>
          )
        })}
      </nav>
    </header>
  )
}
