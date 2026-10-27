import { Pause, Play, Radar, SkipBack, SkipForward, Star, Volume1, Volume2, VolumeX } from 'lucide-react'
import { Slider } from '@/components/ui/slider'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'

type Props = {
  playing: boolean
  favorite: boolean
  scanning: boolean
  volume: number
  onPrev: () => void
  onNext: () => void
  onPlay: () => void
  onFavorite: () => void
  onScan: () => void
  onVolume: (v: number) => void
}

function Key({
  label,
  hint,
  pressed,
  onClick,
  className,
  children,
}: {
  label: string
  hint?: string
  pressed?: boolean
  onClick: () => void
  className?: string
  children: React.ReactNode
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          aria-label={label}
          aria-pressed={pressed}
          onClick={onClick}
          className={cn('key relative inline-grid h-12 w-full place-items-center rounded-[calc(var(--radius)*0.7)] px-3 sm:w-auto sm:min-w-12', className)}
        >
          {pressed !== undefined && <span className="key-lamp absolute top-1.5 left-1/2 h-1 w-4 -translate-x-1/2 rounded-full" />}
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent>
        {label}
        {hint && <span className="ml-2 opacity-60">{hint}</span>}
      </TooltipContent>
    </Tooltip>
  )
}

// The row of radio keys under the meters, and the volume knob as a slider.
export function Controls(p: Props) {
  const VolumeIcon = p.volume === 0 ? VolumeX : p.volume < 0.5 ? Volume1 : Volume2
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <div className="grid grid-cols-[1fr_1.4fr_1fr_1fr_1fr] gap-2.5 sm:flex sm:gap-3">
        <Key label="Previous station" hint="←" onClick={p.onPrev}>
          <SkipBack className="size-5" aria-hidden="true" />
        </Key>
        <Key label={p.playing ? 'Pause' : 'Play'} hint="Space" onClick={p.onPlay} className="sm:w-20">
          {p.playing ? <Pause className="size-6" aria-hidden="true" /> : <Play className="size-6" aria-hidden="true" />}
        </Key>
        <Key label="Next station" hint="→" onClick={p.onNext}>
          <SkipForward className="size-5" aria-hidden="true" />
        </Key>
        <Key label={p.favorite ? 'Remove from favorites' : 'Add to favorites'} hint="F" pressed={p.favorite} onClick={p.onFavorite}>
          <Star className={cn('size-5', p.favorite && 'fill-current')} aria-hidden="true" />
        </Key>
        <Key label="Scan the dial" hint="S" pressed={p.scanning} onClick={p.onScan}>
          <Radar className="size-5" aria-hidden="true" />
        </Key>
      </div>
      <label className="engraved flex min-w-[9rem] flex-1 items-center gap-3 sm:ml-auto sm:max-w-64">
        <VolumeIcon className="size-5 shrink-0" aria-hidden="true" />
        <span className="sr-only">Volume</span>
        <Slider
          value={[Math.round(p.volume * 100)]}
          max={100}
          step={1}
          onValueChange={([v]) => p.onVolume(v / 100)}
          aria-label="Volume"
          className="volume"
        />
      </label>
    </div>
  )
}
