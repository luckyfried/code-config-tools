export type Priority = "high" | "normal" | "low"

export interface Item {
  id: string
  name: string
  price: number
  url?: string
  image?: string
  note?: string
  priority?: Priority
  claimed?: boolean
}

export interface Owner {
  name: string
  phone?: string
  email?: string
}

export interface Config {
  owner: Owner
  occasion: string
  currency: string
  items: Item[]
  theme?: string
  copy?: Record<string, string>
}

export type Copy = Record<string, string>

declare global {
  interface Window {
    __APP_CONFIG__?: Partial<Config>
    __APP_COPY__?: Copy
  }
}

export function slug(text: string): string {
  return (
    text
      .toLowerCase()
      .normalize("NFKD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "item"
  )
}

export function readConfig(): Config {
  const raw = window.__APP_CONFIG__ ?? {}
  const seen = new Set<string>()
  const items = (raw.items ?? []).map((item) => {
    let id = item.id || slug(item.name)
    for (let n = 2; seen.has(id); n++) id = `${slug(item.name)}-${n}`
    seen.add(id)
    return { ...item, id }
  })
  return {
    owner: raw.owner ?? { name: "" },
    occasion: raw.occasion ?? "",
    currency: raw.currency ?? "USD",
    items,
    theme: raw.theme,
    copy: raw.copy,
  }
}

export function readCopy(config: Config): Copy {
  return { ...(window.__APP_COPY__ ?? {}), ...(config.copy ?? {}) }
}

/** Fills {name} slots in a line of copy. */
export function fill(line: string | undefined, vars: Record<string, string | number>): string {
  return (line ?? "").replace(/\{(\w+)\}/g, (_, key: string) => String(vars[key] ?? ""))
}
