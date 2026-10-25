import { GlassWater } from "lucide-react"
import { cn } from "@/lib/utils"

const GLASSES = 8

export function WaterCounter({ count, onChange }: { count: number; onChange: (n: number) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="flex items-baseline justify-between text-sm">
        <span className="font-semibold">Water</span>
        <span className="text-muted-foreground tabular-nums">
          {count} of {GLASSES} glasses
        </span>
      </p>
      <div role="group" aria-label="Glasses of water" className="grid grid-cols-8 gap-1">
        {Array.from({ length: GLASSES }, (_, i) => {
          const full = i < count
          return (
            <button
              key={i}
              type="button"
              aria-label={`${i + 1} ${i ? "glasses" : "glass"}`}
              aria-pressed={full}
              onClick={() => onChange(count === i + 1 ? i : i + 1)}
              className={cn(
                "tile-press flex h-10 min-w-0 items-center justify-center rounded-full outline-none transition-colors focus-visible:ring-3 focus-visible:ring-ring/50",
                full ? "bg-water/15 text-water" : "text-muted-foreground/50",
              )}
            >
              <GlassWater className="size-5" />
            </button>
          )
        })}
      </div>
    </div>
  )
}
