import { cn } from "@/lib/utils"
import type { Food } from "@/lib/config"
import { fmt } from "@/lib/nutrition"
import { FoodDisc } from "./FoodDisc"

/** The person's foods as large tiles, in the order the time of day suggests. */
export function QuickTray({ foods, onPick, layout }: { foods: Food[]; onPick: (f: Food) => void; layout: "row" | "grid" }) {
  return (
    <ul
      aria-label="Quick add"
      className={cn(
        layout === "row"
          ? "scroll-row flex scroll-px-4 gap-2 overflow-x-auto px-4 pb-1"
          : "grid grid-cols-[repeat(auto-fill,minmax(6.5rem,1fr))] gap-2",
      )}
    >
      {foods.map((f) => (
        <li key={f.id} className={cn(layout === "row" && "w-[6.5rem] shrink-0")}>
          <button
            type="button"
            onClick={() => onPick(f)}
            className="tile-press flex h-full w-full flex-col items-start gap-1.5 rounded-xl border bg-card p-2.5 text-left lg:gap-2 lg:p-3 outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <FoodDisc food={f} className="size-9 text-base lg:size-10 lg:text-lg" />
            <span className="line-clamp-2 min-h-10 text-sm font-medium text-pretty">{f.name}</span>
            <span className="text-xs text-muted-foreground tabular-nums">{fmt(f.calories)} kcal</span>
          </button>
        </li>
      ))}
    </ul>
  )
}
