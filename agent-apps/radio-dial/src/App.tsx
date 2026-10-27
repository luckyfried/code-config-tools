import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Command as CommandIcon, Heart, Radio, Search } from 'lucide-react'
import { toast } from 'sonner'
import { CardIndex, type View } from '@/components/CardIndex'
import { Controls } from '@/components/Controls'
import { Dial } from '@/components/Dial'
import { Meters } from '@/components/Meters'
import { Tubes } from '@/components/Tubes'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from '@/components/ui/command'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import { config, type Station } from '@/lib/config'
import { RadioEngine, type Status } from '@/lib/engine'
import { reducedMotion, weakDevice } from '@/lib/motion'
import { loadSaved, parseSaved, type Saved, writeSaved } from '@/lib/store'
import { cn } from '@/lib/utils'

const WARM_MS = 1300
const SCAN_FIRST_MS = 4200
const SCAN_STEP_MS = 3400

const initial = loadSaved()

function clock(seconds: number) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  const h = Math.floor(m / 60)
  const mm = String(m % 60).padStart(2, '0')
  const ss = String(s).padStart(2, '0')
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}

export default function App() {
  const engine = useMemo(() => new RadioEngine(), [])
  const panel = useRef<HTMLDivElement>(null)
  const readout = useRef<HTMLSpanElement>(null)
  const searchRef = useRef<HTMLInputElement>(null)
  const [saved, setSaved] = useState<Saved>(initial.saved)
  const [status, setStatus] = useState<Status>('idle')
  const [warming, setWarming] = useState(true)
  const [locked, setLocked] = useState(false)
  const [scan, setScan] = useState<'off' | 'once' | 'on'>(initial.saved.last ? 'off' : 'once')
  const [failed, setFailed] = useState<Set<string>>(() => new Set())
  const [phoneView, setPhoneView] = useState<'dial' | View>('dial')
  const [sideView, setSideView] = useState<View>('find')
  const [palette, setPalette] = useState(false)
  const [onAir, setOnAir] = useState(0)
  const warmedOnPlay = useRef(false)
  const noBlur = useMemo(() => weakDevice(), [])

  const dial = useMemo(() => {
    const seen = new Set<string>()
    return [...config.presets, ...saved.added].filter((s) => !seen.has(s.id) && !!seen.add(s.id))
  }, [saved.added])
  const presetIds = useMemo(() => new Set(config.presets.map((s) => s.id)), [])
  const [currentId, setCurrentId] = useState<string | null>(() =>
    dial.some((s) => s.id === initial.saved.last) ? initial.saved.last : (dial[0]?.id ?? null),
  )
  const index = Math.max(0, dial.findIndex((s) => s.id === currentId))
  const station: Station | undefined = dial[index]
  const favorites = useMemo(
    () => saved.favorites.map((id) => dial.find((s) => s.id === id)).filter((s): s is Station => !!s),
    [saved.favorites, dial],
  )
  const isFavorite = useCallback((id: string) => saved.favorites.includes(id), [saved.favorites])

  const save = useCallback((change: (s: Saved) => Saved) => {
    setSaved((prev) => {
      const next = change(prev)
      writeSaved(next)
      return next
    })
  }, [])

  useEffect(() => {
    engine.setVolume(initial.saved.volume)
    engine.onChange((s) => setStatus(s))
    const t = window.setTimeout(() => setWarming(false), WARM_MS)
    return () => window.clearTimeout(t)
  }, [engine])

  const live = status === 'playing' || status === 'buffering'
  const latest = useRef({ dial, index, live })
  latest.current = { dial, index, live }

  const startPlay = useCallback(
    (s: Station) => {
      if (!warmedOnPlay.current) {
        warmedOnPlay.current = true
        if (!reducedMotion()) {
          setWarming(true)
          window.setTimeout(() => setWarming(false), WARM_MS)
        }
      }
      setFailed((f) => {
        if (!f.has(s.id)) return f
        const n = new Set(f)
        n.delete(s.id)
        return n
      })
      engine.play(s.url, !reducedMotion(), () => {
        const { dial } = latest.current
        setFailed((f) => new Set(f).add(s.id))
        const at = dial.findIndex((d) => d.id === s.id)
        const next = dial.length > 1 ? dial[(at + 1) % dial.length] : undefined
        if (next && next.id !== s.id) {
          toast(`${s.name} is not answering.`, { description: `Tuning to ${next.name}.` })
          setCurrentId(next.id)
          save((v) => ({ ...v, last: next.id }))
          startPlayRef.current(next)
        } else {
          toast(`${s.name} is not answering.`)
        }
      })
    },
    [engine, save],
  )
  const startPlayRef = useRef(startPlay)
  startPlayRef.current = startPlay

  const tune = useCallback(
    (i: number, opts: { play?: boolean; keepScan?: boolean } = {}) => {
      const { dial, live } = latest.current
      if (!dial.length) return
      const n = ((i % dial.length) + dial.length) % dial.length
      const s = dial[n]
      if (!opts.keepScan) setScan('off')
      setCurrentId(s.id)
      if (!opts.keepScan) save((v) => ({ ...v, last: s.id }))
      if (opts.play || live) startPlay(s)
      else engine.blip(!reducedMotion())
    },
    [engine, save, startPlay],
  )

  const tuneStation = useCallback(
    (s: Station) => {
      const at = latest.current.dial.findIndex((d) => d.id === s.id)
      if (at >= 0) return tune(at, { play: true })
      save((v) => ({ ...v, added: [...v.added, s], last: s.id }))
      setScan('off')
      setCurrentId(s.id)
      startPlay(s)
    },
    [save, startPlay, tune],
  )

  const togglePlay = useCallback(() => {
    setScan((sc) => (sc === 'once' ? 'off' : sc))
    if (latest.current.live) engine.stop()
    else if (station) {
      save((v) => ({ ...v, last: station.id }))
      startPlay(station)
    }
  }, [engine, save, startPlay, station])

  const toggleFavorite = useCallback(
    (s: Station | undefined = station) => {
      if (!s) return
      const on = saved.favorites.includes(s.id)
      save((v) => ({
        ...v,
        added: on || dial.some((d) => d.id === s.id) ? v.added : [...v.added, s],
        favorites: on ? v.favorites.filter((f) => f !== s.id) : [...v.favorites, s.id],
      }))
    },
    [dial, save, saved.favorites, station],
  )

  const addStation = useCallback(
    (s: Station) => {
      save((v) => ({ ...v, added: [...v.added, s] }))
      toast(`${s.name} is on your dial.`)
    },
    [save],
  )

  const removeStation = useCallback(
    (s: Station) => {
      save((v) => ({ ...v, added: v.added.filter((a) => a.id !== s.id), favorites: v.favorites.filter((f) => f !== s.id) }))
      if (s.id === currentId) {
        if (latest.current.live) engine.stop()
        setCurrentId(dial[0]?.id ?? null)
      }
    },
    [currentId, dial, engine, save],
  )

  // Scanning walks the dial one station at a time; the first visit walks it once, the Scan key until pressed again.
  useEffect(() => {
    if (scan === 'off' || dial.length < 2) return
    let stepped = 0
    let timer = 0
    const step = () => {
      const { index, dial } = latest.current
      stepped++
      if (scan === 'once' && stepped >= dial.length) {
        tune(0, { keepScan: true })
        setScan('off')
        return
      }
      tune(index + 1, { keepScan: true })
      timer = window.setTimeout(step, SCAN_STEP_MS)
    }
    timer = window.setTimeout(step, scan === 'once' ? SCAN_FIRST_MS : 1200)
    return () => window.clearTimeout(timer)
  }, [scan, dial.length, tune])

  useEffect(() => {
    if (status !== 'playing') return setOnAir(0)
    const from = Date.now()
    const t = window.setInterval(() => setOnAir(Math.floor((Date.now() - from) / 1000)), 1000)
    return () => window.clearInterval(t)
  }, [status, currentId])

  // The lock screen and the phone's media keys.
  useEffect(() => {
    const ms = navigator.mediaSession
    if (!ms || !station) return
    const art = station.logo ?? './icon.svg'
    ms.metadata = new MediaMetadata({
      title: station.name,
      artist: station.about ?? station.country ?? '',
      album: config.name,
      artwork: [{ src: new URL(art, location.href).href, sizes: '512x512', type: art.endsWith('.svg') ? 'image/svg+xml' : 'image/png' }],
    })
    ms.playbackState = live ? 'playing' : 'paused'
    const handlers: [MediaSessionAction, () => void][] = [
      ['play', () => !latest.current.live && togglePlay()],
      ['pause', () => latest.current.live && togglePlay()],
      ['stop', () => engine.stop()],
      ['previoustrack', () => tune(latest.current.index - 1, { play: true })],
      ['nexttrack', () => tune(latest.current.index + 1, { play: true })],
    ]
    for (const [action, fn] of handlers) {
      try {
        ms.setActionHandler(action, fn)
      } catch {
        // A browser without this action leaves it to the default.
      }
    }
  }, [engine, live, station, togglePlay, tune])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPalette((p) => !p)
        return
      }
      const el = e.target as HTMLElement
      if (palette || e.metaKey || e.ctrlKey || e.altKey || el.closest('input, textarea, [role="dialog"], [role="slider"], [role="radio"], [role="tab"]')) return
      const { index } = latest.current
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        tune(index - 1)
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        tune(index + 1)
      } else if (e.key === ' ' && !el.closest('button')) {
        e.preventDefault()
        togglePlay()
      } else if (e.key === 'f') toggleFavorite()
      else if (e.key === 's') setScan((s) => (s === 'on' ? 'off' : 'on'))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [palette, toggleFavorite, togglePlay, tune])

  // Any touch or key from the person ends the first-visit walk, so the dial stays where they put it.
  useEffect(() => {
    if (scan !== 'once') return
    const stop = () => setScan('off')
    window.addEventListener('pointerdown', stop, { once: true })
    return () => window.removeEventListener('pointerdown', stop)
  }, [scan])

  const exportSaved = () => {
    const blob = new Blob([JSON.stringify({ added: saved.added, favorites: saved.favorites, last: saved.last, volume: saved.volume }, null, 2)], {
      type: 'application/json',
    })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'radio-dial-favorites.json'
    a.click()
    window.setTimeout(() => URL.revokeObjectURL(a.href), 1000)
  }

  const importSaved = (file: File) => {
    file
      .text()
      .then((text) => {
        const got = parseSaved(JSON.parse(text))
        save((v) => {
          const ids = new Set([...config.presets, ...v.added].map((s) => s.id))
          return {
            ...v,
            added: [...v.added, ...got.added.filter((s) => !ids.has(s.id))],
            favorites: [...new Set([...v.favorites, ...got.favorites])],
          }
        })
        toast(`Imported ${got.favorites.length} favorite${got.favorites.length === 1 ? '' : 's'} and ${got.added.length} station${got.added.length === 1 ? '' : 's'}.`)
      })
      .catch(() => toast('That file is not a Radio Dial export.'))
  }

  const strength = !locked ? 0.7 : status === 'playing' ? 1 : status === 'buffering' ? 0.55 : 0.9
  const state =
    status === 'playing'
      ? 'On air'
      : status === 'buffering'
        ? 'Tuning'
        : status === 'failed'
          ? 'Not answering'
          : scan !== 'off'
            ? 'Scanning'
            : 'Standby'
  const nowLine = station?.about ?? station?.country ?? 'Live stream'

  const cardProps = {
    dial,
    presetIds,
    currentId,
    favorites,
    isFavorite,
    onTune: tuneStation,
    onAdd: addStation,
    onRemove: removeStation,
    onFavorite: toggleFavorite,
    onExport: exportSaved,
    onImport: importSaved,
    searchRef,
  }

  const openFind = () => {
    setPalette(false)
    setSideView('find')
    setPhoneView('find')
    window.setTimeout(() => searchRef.current?.focus(), 60)
  }

  return (
    <TooltipProvider delayDuration={400}>
      <div
        ref={panel}
        data-panel
        className={cn(
          'flex h-dvh flex-col overflow-hidden lg:flex-row lg:gap-6 lg:p-6',
          warming && 'warming',
          noBlur && 'no-blur',
        )}
      >
        <main
          className={cn(
            'cabinet flex min-h-0 flex-1 flex-col p-2.5 pt-[max(0.625rem,env(safe-area-inset-top))] lg:rounded-[1.9rem] lg:p-5',
            phoneView !== 'dial' && 'max-lg:hidden',
          )}
        >
          <section className="plate flex min-h-0 flex-1 flex-col gap-3 rounded-[1.25rem] p-4 lg:gap-4 lg:rounded-[1.35rem] lg:p-6">
            <header className="engraved flex h-8 items-center gap-3">
              <Radio className="size-5 shrink-0" aria-hidden="true" />
              <h1 className="font-heading min-w-0 truncate text-lg font-semibold tracking-[0.2em] uppercase">{config.name}</h1>
              <span className="ml-auto flex items-center gap-2 text-sm font-medium tracking-[0.14em] uppercase">
                <span
                  className={cn(
                    'lamp-dot size-2.5 rounded-full',
                    status === 'idle' && scan === 'off' && 'is-off',
                    (status === 'buffering' || scan !== 'off') && 'is-blink',
                  )}
                  aria-hidden="true"
                />
                <span aria-live="polite">{state}</span>
              </span>
              <span className="text-sm font-medium whitespace-nowrap tabular-nums">
                <span ref={readout}>88.0</span> MHz
              </span>
              <button
                type="button"
                onClick={() => setPalette(true)}
                className="key hidden h-8 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium lg:inline-flex"
                aria-label="Open the command palette"
              >
                <CommandIcon className="size-3.5" aria-hidden="true" />K
              </button>
            </header>

            <Tubes
              text={(station?.name ?? config.name).toUpperCase()}
              label={station?.name ?? config.name}
              className="[--tube-max:2.6rem] sm:[--tube-max:3.6rem] lg:[--tube-max:4.4rem]"
            />

            <p className="engraved flex min-h-6 items-start gap-3 text-[15px] leading-6">
              <span className="line-clamp-2 min-w-0 flex-1 sm:line-clamp-1">{nowLine}</span>
              {status === 'playing' ? (
                <span className="engraved-soft shrink-0 tabular-nums">On air {clock(onAir)}</span>
              ) : (
                station?.country && station.about && <span className="engraved-soft shrink-0">{station.country}</span>
              )}
            </p>

            <div className="flex min-h-[150px] flex-[2_1_0] flex-col lg:flex-[3_1_0]">
              {dial.length ? (
                <Dial
                  stations={dial}
                  index={index}
                  failed={failed}
                  warming={warming}
                  panel={panel}
                  readout={readout}
                  onPick={(i) => tune(i, { play: true })}
                  onLock={setLocked}
                />
              ) : (
                <div className="dial-bezel grid h-full place-items-center rounded-[var(--radius)] p-6 text-center">
                  <p className="engraved">Add a station from Find and it takes its place on the dial.</p>
                </div>
              )}
            </div>

            <Meters
              engine={engine}
              seed={station?.id ?? 'radio-dial'}
              strength={strength}
              className="min-h-[190px] flex-[2_1_0] grid-rows-[1.35fr_1fr] lg:min-h-[140px] lg:grid-rows-1"
            />

            <Controls
              playing={live}
              favorite={!!station && isFavorite(station.id)}
              scanning={scan !== 'off'}
              volume={saved.volume}
              onPrev={() => tune(index - 1)}
              onNext={() => tune(index + 1)}
              onPlay={togglePlay}
              onFavorite={() => toggleFavorite()}
              onScan={() => setScan((s) => (s === 'on' ? 'off' : 'on'))}
              onVolume={(v) => {
                engine.setVolume(v)
                save((s) => ({ ...s, volume: v }))
              }}
            />
          </section>
        </main>

        <aside
          className={cn(
            'flex min-h-0 flex-col gap-3 max-lg:flex-1 max-lg:px-4 max-lg:pt-[max(1rem,env(safe-area-inset-top))] lg:w-[400px] xl:w-[440px]',
            phoneView === 'dial' && 'max-lg:hidden',
          )}
        >
          <h2 className="font-heading text-2xl font-semibold tracking-[0.12em] uppercase lg:hidden">
            {phoneView === 'favorites' ? 'Favorites' : 'Find stations'}
          </h2>
          <Tabs value={sideView} onValueChange={(v) => setSideView(v as View)} className="max-lg:hidden">
            <TabsList className="h-11! w-full">
              <TabsTrigger value="find" className="font-heading flex-1 text-base tracking-[0.1em] uppercase">
                Find
              </TabsTrigger>
              <TabsTrigger value="favorites" className="font-heading flex-1 text-base tracking-[0.1em] uppercase">
                Favorites
              </TabsTrigger>
            </TabsList>
          </Tabs>
          <div className="flex min-h-0 flex-1 flex-col max-lg:hidden">
            <CardIndex view={sideView} {...cardProps} />
          </div>
          {phoneView !== 'dial' && (
            <div className="flex min-h-0 flex-1 flex-col lg:hidden">
              <CardIndex view={phoneView} {...cardProps} />
            </div>
          )}
        </aside>

        <nav className="nav-bar bg-card grid shrink-0 grid-cols-3 border-t lg:hidden" aria-label="Screens">
          {(
            [
              ['dial', 'Dial', Radio],
              ['find', 'Find', Search],
              ['favorites', 'Favorites', Heart],
            ] as const
          ).map(([id, label, Icon]) => (
            <button
              key={id}
              type="button"
              onClick={() => setPhoneView(id)}
              aria-current={phoneView === id ? 'page' : undefined}
              className={cn(
                'font-heading flex h-16 flex-col items-center justify-center gap-1 text-sm font-medium tracking-[0.1em] uppercase transition-colors',
                phoneView === id ? 'text-foreground' : 'text-muted-foreground',
              )}
            >
              <Icon className={cn('size-5', phoneView === id && 'text-[var(--glow)]')} aria-hidden="true" />
              {label}
            </button>
          ))}
        </nav>

        <CommandDialog open={palette} onOpenChange={setPalette} title="Radio Dial" description="Tune a station or run a radio action.">
          <CommandInput placeholder="Tune a station or run an action…" />
          <CommandList>
            <CommandEmpty>Nothing on the dial matches.</CommandEmpty>
            <CommandGroup heading="On your dial">
              {dial.map((s, i) => (
                <CommandItem
                  key={s.id}
                  value={`${s.name} ${s.country ?? ''}`}
                  onSelect={() => {
                    setPalette(false)
                    tune(i, { play: true })
                  }}
                >
                  <Radio aria-hidden="true" />
                  {s.name}
                  {s.country && <CommandShortcut>{s.country}</CommandShortcut>}
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandGroup heading="Radio">
              <CommandItem onSelect={() => (setPalette(false), togglePlay())}>
                {live ? 'Pause' : 'Play'}
                <CommandShortcut>Space</CommandShortcut>
              </CommandItem>
              <CommandItem onSelect={() => (setPalette(false), tune(index + 1))}>
                Next station
                <CommandShortcut>→</CommandShortcut>
              </CommandItem>
              <CommandItem onSelect={() => (setPalette(false), tune(index - 1))}>
                Previous station
                <CommandShortcut>←</CommandShortcut>
              </CommandItem>
              <CommandItem onSelect={() => (setPalette(false), toggleFavorite())}>
                {station && isFavorite(station.id) ? 'Remove from favorites' : 'Add to favorites'}
                <CommandShortcut>F</CommandShortcut>
              </CommandItem>
              <CommandItem onSelect={() => (setPalette(false), setScan((s) => (s === 'on' ? 'off' : 'on')))}>
                {scan === 'on' ? 'Stop scanning' : 'Scan the dial'}
                <CommandShortcut>S</CommandShortcut>
              </CommandItem>
              <CommandItem onSelect={openFind}>Find stations by name, genre, or country</CommandItem>
            </CommandGroup>
          </CommandList>
        </CommandDialog>
        <Toaster position="top-center" />
      </div>
    </TooltipProvider>
  )
}
