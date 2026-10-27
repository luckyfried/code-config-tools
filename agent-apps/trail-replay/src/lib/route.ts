/** Hash routes, so a reload under any folder or subpath lands on the same screen. */
import { useSyncExternalStore } from "react"

export type Route = { screen: "replay"; id: string | null } | { screen: "activities" } | { screen: "poster"; id: string | null }

function parse(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent)
  if (parts[0] === "activities") return { screen: "activities" }
  if (parts[0] === "poster") return { screen: "poster", id: parts[1] ?? null }
  return { screen: "replay", id: parts[1] ?? null }
}

const subscribe = (fn: () => void) => {
  window.addEventListener("hashchange", fn)
  return () => window.removeEventListener("hashchange", fn)
}

export function useRoute(): Route {
  const hash = useSyncExternalStore(subscribe, () => window.location.hash)
  return parse(hash)
}

export function href(route: Route) {
  if (route.screen === "activities") return "#/activities"
  const id = route.id ? `/${encodeURIComponent(route.id)}` : ""
  return `#/${route.screen}${id}`
}
