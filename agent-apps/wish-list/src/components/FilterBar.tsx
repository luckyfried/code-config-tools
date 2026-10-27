import { Shuffle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { RollingNumber } from "@/components/RollingNumber"
import { fill, type Copy } from "@/lib/config"
import type { Band } from "@/lib/money"

export function bandLabel(band: Band, copy: Copy, whole: Intl.NumberFormat): string {
  if (band.low === 0) return fill(copy.under, { amount: whole.format(band.high) })
  if (band.high === Infinity) return fill(copy.over, { amount: whole.format(band.low) })
  return fill(copy.between, { low: whole.format(band.low), high: whole.format(band.high) })
}

function HideGotten({ className, on, label, onChange }: { className: string; on: boolean; label: string; onChange: (on: boolean) => void }) {
  return (
    <label className={`shrink-0 cursor-pointer items-center gap-2 text-[0.84rem] font-medium lg:text-[0.88rem] whitespace-nowrap text-foreground/80 select-none ${className}`}>
      <Switch checked={on} onCheckedChange={onChange} />
      {label}
    </label>
  )
}

export function FilterBar({
  copy,
  total,
  open,
  count,
  format,
  whole,
  bands,
  band,
  hideGotten,
  onBand,
  onHideGotten,
  onShuffle,
}: {
  copy: Copy
  total: number
  open: number
  count: number
  format: Intl.NumberFormat
  whole: Intl.NumberFormat
  bands: Band[]
  band: string
  hideGotten: boolean
  onBand: (id: string) => void
  onHideGotten: (on: boolean) => void
  onShuffle: () => void
}) {
  const chip =
    "h-9 rounded-full border border-border bg-card/70 px-4 text-[0.88rem] font-medium text-foreground/80 shadow-xs data-[state=on]:border-primary data-[state=on]:bg-primary data-[state=on]:text-primary-foreground hover:data-[state=on]:bg-primary"
  return (
    <div className="bar sticky top-0 z-30 border-b border-border/70 print-hide">
      <div className="mx-auto flex w-full max-w-[1600px] flex-col gap-2.5 px-4 py-3 sm:px-6 lg:flex-row lg:items-center lg:gap-6 lg:px-10">
        <div className="flex items-center justify-between gap-2 lg:justify-start">
          <div className="flex items-center gap-2" aria-live="polite">
            <RollingNumber value={total} format={format} className="display text-[1.5rem] font-semibold text-primary lg:text-[1.75rem]" />
            <span className="flex flex-col text-[0.78rem] leading-tight min-[380px]:whitespace-nowrap text-muted-foreground lg:block lg:text-[0.9rem]">
              <span>{copy.leftToGive}</span>
              <span className="hidden text-foreground/40 lg:inline"> · </span>
              <span>{fill(copy.openCount, { open, count })}</span>
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-2 lg:hidden">
            <HideGotten className="flex" on={hideGotten} label={copy.hideGotten} onChange={onHideGotten} />
            <Button variant="outline" size="icon" className="size-9 rounded-full" aria-label={copy.shuffle} title={copy.shuffle} onClick={onShuffle}>
              <Shuffle className="size-4" />
            </Button>
          </div>
        </div>
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <div className="no-scrollbar fade-end -mx-4 flex min-w-0 flex-1 items-center overflow-x-auto pr-12 pl-4 sm:mx-0 sm:pl-0 lg:pr-0">
            <ToggleGroup
              type="single"
              value={band}
              onValueChange={(v) => v && onBand(v)}
              spacing={2}
              aria-label={copy.priceFilter}
            >
              <ToggleGroupItem value="all" className={chip}>
                {copy.everything}
              </ToggleGroupItem>
              {bands.map((b) => (
                <ToggleGroupItem key={b.id} value={b.id} className={chip}>
                  {bandLabel(b, copy, whole)}
                </ToggleGroupItem>
              ))}
            </ToggleGroup>
          </div>
          <HideGotten className="hidden lg:flex" on={hideGotten} label={copy.hideGotten} onChange={onHideGotten} />
          <Button variant="outline" className="hidden h-9 shrink-0 gap-2 rounded-full px-4 lg:inline-flex" onClick={onShuffle}>
            <Shuffle className="size-4" />
            {copy.shuffle}
          </Button>
        </div>
      </div>
    </div>
  )
}
