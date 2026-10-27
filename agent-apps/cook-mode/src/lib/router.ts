import { useSyncExternalStore } from "react"

export type Route =
  | { name: "index" }
  | { name: "recipe"; id: string }
  | { name: "cook"; id: string; step: number }
  | { name: "shopping" }

function parse(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent)
  if (parts[0] === "recipe" && parts[1]) return { name: "recipe", id: parts[1] }
  if (parts[0] === "cook" && parts[1]) {
    const step = Math.max(1, Number(parts[2]) || 1)
    return { name: "cook", id: parts[1], step }
  }
  if (parts[0] === "shopping") return { name: "shopping" }
  return { name: "index" }
}

function subscribe(listener: () => void) {
  window.addEventListener("hashchange", listener)
  return () => window.removeEventListener("hashchange", listener)
}

const getHash = () => window.location.hash

export function useRoute() {
  const hash = useSyncExternalStore(subscribe, getHash, () => "")
  return parse(hash)
}

export function href(route: Route) {
  switch (route.name) {
    case "recipe":
      return `#/recipe/${encodeURIComponent(route.id)}`
    case "cook":
      return `#/cook/${encodeURIComponent(route.id)}/${route.step}`
    case "shopping":
      return "#/shopping"
    default:
      return "#/"
  }
}

export function go(route: Route, replace = false) {
  const next = href(route)
  if (replace) window.history.replaceState(null, "", next)
  else window.location.hash = next
  if (replace) window.dispatchEvent(new HashChangeEvent("hashchange"))
}
