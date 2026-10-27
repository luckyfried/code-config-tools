import type { Station } from './config'

// Everything the person does on this page lives under one localStorage key, named after the app.
const KEY = 'radio-dial'

export type Saved = {
  added: Station[]
  favorites: string[]
  last: string | null
  volume: number
}

const empty: Saved = { added: [], favorites: [], last: null, volume: 0.8 }

function isStation(s: unknown): s is Station {
  const o = s as Station
  return !!o && typeof o.id === 'string' && typeof o.name === 'string' && typeof o.url === 'string' && o.url.startsWith('https://')
}

export function parseSaved(value: unknown): Saved {
  const o = (value ?? {}) as Partial<Saved>
  return {
    added: Array.isArray(o.added) ? o.added.filter(isStation) : [],
    favorites: Array.isArray(o.favorites) ? o.favorites.filter((f): f is string => typeof f === 'string') : [],
    last: typeof o.last === 'string' ? o.last : null,
    volume: typeof o.volume === 'number' && o.volume >= 0 && o.volume <= 1 ? o.volume : empty.volume,
  }
}

export function loadSaved(): { saved: Saved; firstVisit: boolean } {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return { saved: { ...empty }, firstVisit: true }
    return { saved: parseSaved(JSON.parse(raw)), firstVisit: false }
  } catch {
    return { saved: { ...empty }, firstVisit: true }
  }
}

export function writeSaved(saved: Saved) {
  try {
    localStorage.setItem(KEY, JSON.stringify(saved))
  } catch {
    // A full or blocked storage keeps the session working; nothing is lost from the screen.
  }
}
