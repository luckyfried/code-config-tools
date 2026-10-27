const KEY = "wish-list"

export interface Saved {
  band: string
  hideGotten: boolean
  order: string[]
  promised: string[]
}

export function loadSaved(): Saved | null {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const data = JSON.parse(raw) as Partial<Saved>
    return {
      band: typeof data.band === "string" ? data.band : "all",
      hideGotten: data.hideGotten === true,
      order: Array.isArray(data.order) ? data.order.filter((id) => typeof id === "string") : [],
      promised: Array.isArray(data.promised) ? data.promised.filter((id) => typeof id === "string") : [],
    }
  } catch {
    return null
  }
}

export function save(state: Saved): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(state))
  } catch {
    /* A browser with storage turned off keeps the choices for this visit only. */
  }
}
