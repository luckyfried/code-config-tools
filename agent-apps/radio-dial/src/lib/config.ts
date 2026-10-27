// The person's inputs, written by run.py into config.js as window.__APP_CONFIG__ before any module runs.

export type Station = {
  id: string
  name: string
  url: string
  homepage?: string
  country?: string
  logo?: string
  about?: string
  tags?: string
}

export type AppConfig = {
  name: string
  presets: Station[]
  theme: string
}

type RawPreset = Partial<Record<keyof Station, unknown>>

declare global {
  interface Window {
    __APP_CONFIG__?: { name?: unknown; presets?: RawPreset[]; theme?: unknown }
  }
}

const text = (v: unknown) => (typeof v === 'string' && v.trim() ? v.trim() : undefined)

export function stationId(url: string) {
  return url.trim()
}

function readConfig(): AppConfig {
  const raw = window.__APP_CONFIG__ ?? {}
  const presets: Station[] = []
  for (const p of Array.isArray(raw.presets) ? raw.presets : []) {
    const url = text(p.url)
    const name = text(p.name)
    if (!url || !name) continue
    presets.push({
      id: stationId(url),
      name,
      url,
      homepage: text(p.homepage),
      country: text(p.country),
      logo: text(p.logo),
      about: text(p.about),
    })
  }
  return { name: text(raw.name) ?? 'Radio Dial', presets, theme: text(raw.theme) ?? 'walnut' }
}

export const config = readConfig()
