import { useEffect, useRef, useState } from 'react'
import { Download, Loader2, Minus, Play, Plus, Search, Star, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import type { Station } from '@/lib/config'
import { type FindBy, search } from '@/lib/radiobrowser'
import { cn } from '@/lib/utils'

export type View = 'find' | 'favorites'

type Props = {
  view: View
  dial: Station[]
  presetIds: Set<string>
  currentId: string | null
  favorites: Station[]
  isFavorite: (id: string) => boolean
  onTune: (s: Station) => void
  onAdd: (s: Station) => void
  onRemove: (s: Station) => void
  onFavorite: (s: Station) => void
  onExport: () => void
  onImport: (file: File) => void
  searchRef?: React.RefObject<HTMLInputElement | null>
}

const PLACEHOLDER: Record<FindBy, string> = {
  name: 'Station name, like KEXP',
  tag: 'Genre, like jazz or ambient',
  country: 'Country, like Japan',
}

type Found = { state: 'idle' } | { state: 'busy' } | { state: 'done'; rows: Station[] } | { state: 'error'; message: string }

function Card({ s, i, p }: { s: Station; i: number; p: Props }) {
  const onDial = p.dial.some((d) => d.id === s.id)
  const fav = p.isFavorite(s.id)
  const line = [s.country, s.tags].filter(Boolean).join(' · ')
  return (
    <li
      className={cn('index-card card-in rounded-[calc(var(--radius)*0.5)] px-4 pt-2.5 pb-3', p.currentId === s.id && 'is-current')}
      style={{ '--i': i } as React.CSSProperties}
    >
      <div className="flex h-7 items-center gap-2">
        <h3 className="font-heading min-w-0 flex-1 truncate text-lg leading-none font-semibold tracking-wide">{s.name}</h3>
        <button
          type="button"
          onClick={() => p.onFavorite(s)}
          aria-pressed={fav}
          aria-label={fav ? `Remove ${s.name} from favorites` : `Add ${s.name} to favorites`}
          className="index-soft -mr-1.5 grid size-9 place-items-center rounded-full transition-transform active:scale-[0.94]"
        >
          <Star className={cn('size-[18px]', fav && 'fill-current text-[var(--paper-rule)]')} aria-hidden="true" />
        </button>
      </div>
      <div className="index-lines mt-2">
        <p className="index-soft truncate text-sm leading-[1.45rem]">{line || 'Live stream'}</p>
        {s.about && <p className="line-clamp-2 text-sm leading-[1.45rem]">{s.about}</p>}
      </div>
      <div className="mt-2 flex items-center gap-2">
        <Button size="sm" onClick={() => p.onTune(s)} className="h-8 gap-1.5">
          <Play className="size-3.5" aria-hidden="true" />
          Tune
        </Button>
        {!onDial && (
          <Button size="sm" variant="outline" onClick={() => p.onAdd(s)} className="h-8 gap-1.5 bg-transparent">
            <Plus className="size-3.5" aria-hidden="true" />
            Add to dial
          </Button>
        )}
        {onDial && !p.presetIds.has(s.id) && (
          <Button size="sm" variant="ghost" onClick={() => p.onRemove(s)} className="h-8 gap-1.5">
            <Minus className="size-3.5" aria-hidden="true" />
            Take off dial
          </Button>
        )}
        {onDial && p.presetIds.has(s.id) && <span className="index-soft ml-1 text-xs tracking-wide uppercase">Preset</span>}
      </div>
    </li>
  )
}

function Cards({ rows, p, keyBase }: { rows: Station[]; p: Props; keyBase: string }) {
  return (
    <ul className="grid gap-3 pb-4" key={keyBase}>
      {rows.map((s, i) => (
        <Card key={s.id} s={s} i={i} p={p} />
      ))}
    </ul>
  )
}

function Note({ children }: { children: React.ReactNode }) {
  return <p className="text-muted-foreground px-1 py-6 text-center text-sm">{children}</p>
}

// Search, results, and favorites as a paper card index; results slide in card by card.
export function CardIndex(p: Props) {
  const [by, setBy] = useState<FindBy>('name')
  const [query, setQuery] = useState('')
  const [found, setFound] = useState<Found>({ state: 'idle' })
  const file = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) {
      setFound({ state: 'idle' })
      return
    }
    const ctl = new AbortController()
    const t = window.setTimeout(() => {
      setFound({ state: 'busy' })
      search(by, q, ctl.signal)
        .then((rows) => setFound({ state: 'done', rows }))
        .catch((e: Error) => {
          if (ctl.signal.aborted) return
          setFound({ state: 'error', message: `The station directory did not answer: ${e.message}` })
        })
    }, 350)
    return () => {
      window.clearTimeout(t)
      ctl.abort()
    }
  }, [by, query])

  if (p.view === 'favorites') {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-3">
        <div className="min-h-0 flex-1 overflow-y-auto pr-1">
          {p.favorites.length ? (
            <Cards rows={p.favorites} p={p} keyBase="favorites" />
          ) : (
            <Note>Star a station on the dial or in Find, and it waits here.</Note>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="flex-1 gap-2" onClick={p.onExport}>
            <Download className="size-4" aria-hidden="true" />
            Export
          </Button>
          <Button variant="outline" className="flex-1 gap-2" onClick={() => file.current?.click()}>
            <Upload className="size-4" aria-hidden="true" />
            Import
          </Button>
          <input
            ref={file}
            type="file"
            accept="application/json,.json"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) p.onImport(f)
              e.target.value = ''
            }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="relative">
        <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2" aria-hidden="true" />
        <Input
          ref={p.searchRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={PLACEHOLDER[by]}
          aria-label="Find stations"
          className="bg-card h-11 pl-9"
          type="search"
          enterKeyHint="search"
        />
        {found.state === 'busy' && (
          <Loader2 className="text-muted-foreground absolute top-1/2 right-3 size-4 -translate-y-1/2 animate-spin" aria-label="Searching" />
        )}
      </div>
      <ToggleGroup
        type="single"
        value={by}
        onValueChange={(v) => v && setBy(v as FindBy)}
        variant="outline"
        className="w-full"
        aria-label="Find by"
      >
        <ToggleGroupItem value="name" className="flex-1">
          Name
        </ToggleGroupItem>
        <ToggleGroupItem value="tag" className="flex-1">
          Genre
        </ToggleGroupItem>
        <ToggleGroupItem value="country" className="flex-1">
          Country
        </ToggleGroupItem>
      </ToggleGroup>
      <div className="min-h-0 flex-1 overflow-y-auto pr-1" aria-live="polite">
        {found.state === 'idle' && (
          <>
            <h2 className="font-heading text-muted-foreground mb-2 px-1 text-sm font-medium tracking-[0.14em] uppercase">On your dial</h2>
            <Cards rows={p.dial} p={p} keyBase="dial" />
          </>
        )}
        {found.state === 'busy' && <Note>Searching the station directory…</Note>}
        {found.state === 'error' && <Note>{found.message}</Note>}
        {found.state === 'done' &&
          (found.rows.length ? (
            <Cards rows={found.rows} p={p} keyBase={`${by}:${query}`} />
          ) : (
            <Note>No station with an https stream matches “{query.trim()}”.</Note>
          ))}
      </div>
    </div>
  )
}
