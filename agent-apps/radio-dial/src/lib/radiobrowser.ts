import type { Station } from './config'

// Live search against Radio Browser, the community station directory: one mirror picked from its server list,
// broken stations left out, the most voted first, and only https streams kept so the page can play them.

export type FindBy = 'name' | 'tag' | 'country'

let mirror: Promise<string> | null = null

function pickMirror() {
  mirror ??= fetch('https://all.api.radio-browser.info/json/servers')
    .then((r) => r.json() as Promise<{ name: string }[]>)
    .then((list) => {
      const names = [...new Set(list.map((s) => s.name))]
      return names[Math.floor(Math.random() * names.length)] ?? 'de1.api.radio-browser.info'
    })
    .catch(() => 'de1.api.radio-browser.info')
  return mirror
}

type Row = {
  stationuuid: string
  name: string
  url_resolved: string
  homepage: string
  favicon: string
  country: string
  tags: string
  codec: string
  bitrate: number
}

export async function search(by: FindBy, query: string, signal: AbortSignal): Promise<Station[]> {
  const host = await pickMirror()
  const params = new URLSearchParams({ limit: '50', hidebroken: 'true', order: 'votes', reverse: 'true' })
  params.set(by === 'country' ? 'country' : by, query)
  const res = await fetch(`https://${host}/json/stations/search?${params}`, { signal })
  if (!res.ok) throw new Error(`The station directory answered ${res.status}.`)
  const rows = (await res.json()) as Row[]
  const seen = new Set<string>()
  const out: Station[] = []
  for (const r of rows) {
    const url = (r.url_resolved || '').trim()
    if (!url.startsWith('https://') || seen.has(url)) continue
    seen.add(url)
    out.push({
      id: url,
      name: r.name.trim() || 'Unnamed station',
      url,
      homepage: r.homepage || undefined,
      country: r.country || undefined,
      logo: r.favicon?.startsWith('https://') ? r.favicon : undefined,
      tags: r.tags ? r.tags.split(',').slice(0, 3).join(', ') : undefined,
      about: [r.codec, r.bitrate ? `${r.bitrate} kbps` : ''].filter(Boolean).join(' '),
    })
  }
  return out
}
