import { ToggleGroup as ToggleGroupPrimitive } from "radix-ui"
import { WaveMark } from "@/components/wave-mark"
import { addedCounts, config, templateSize } from "@/lib/config"
import { cn } from "@/lib/utils"

type TripPickerProps = {
  chosen: string[]
  onChange: (ids: string[]) => void
  className?: string
}

/** The trip templates as toggles: pick one, or several to compose them into one list. */
export function TripPicker({ chosen, onChange, className }: TripPickerProps) {
  const counts = addedCounts(chosen)
  const composing = chosen.length > 1

  const change = (next: string[]) => {
    // Keep the order the templates were picked in: each one's count is what it adds to the ones before it.
    const kept = chosen.filter((id) => next.includes(id))
    const added = next.filter((id) => !chosen.includes(id))
    onChange([...kept, ...added])
  }

  return (
    <ToggleGroupPrimitive.Root
      type="multiple"
      value={chosen}
      onValueChange={change}
      aria-label="Trip templates"
      className={cn("flex flex-col gap-2", className)}
    >
      {config.templates.map((t) => {
        const on = chosen.includes(t.id)
        const adds = counts.get(t.id) ?? 0
        const size = templateSize(t.id)
        return (
          <ToggleGroupPrimitive.Item
            key={t.id}
            value={t.id}
            className={cn(
              "group/trip flex min-h-14 items-center gap-3 rounded-2xl border-2 bg-card px-3.5 py-2.5 text-left transition-[border-color,box-shadow,transform] duration-200 outline-none active:scale-[0.98] focus-visible:ring-3 focus-visible:ring-ring/50",
              on
                ? "border-bag-line shadow-[0_4px_0_-1px_var(--bag-shadow)]"
                : "border-bag-line/20 hover:border-bag-line/45",
            )}
          >
            <WaveMark on={on} round />
            <span className="flex min-w-0 flex-1 flex-col">
              <span className="truncate text-base font-medium">{t.label}</span>
              <span className="text-sm tabular-nums text-muted-foreground">{size} things</span>
            </span>
            {on && composing ? (
              <span key={`${t.id}-${adds}`} className="note-in shrink-0 rounded-full bg-bag/15 px-2.5 py-1 text-sm font-semibold tabular-nums text-foreground">
                +{adds}
              </span>
            ) : null}
          </ToggleGroupPrimitive.Item>
        )
      })}
    </ToggleGroupPrimitive.Root>
  )
}
