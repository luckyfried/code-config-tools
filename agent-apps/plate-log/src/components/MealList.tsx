import { Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { Food } from "@/lib/config"
import { fmt, servingsText, totals, type Entry } from "@/lib/nutrition"
import { cn } from "@/lib/utils"
import { FoodDisc } from "./FoodDisc"

type Props = {
  meals: string[]
  entries: Entry[]
  foods: Map<string, Food>
  fresh: Set<string>
  /** Tighter rows for the desktop card beside the rings. */
  dense?: boolean
  onEdit: (e: Entry, f: Food) => void
  onAdd: (meal: string) => void
}

/** One serving reads as the serving itself; any other amount names how many servings and what one is. */
function portion(servings: number, serving: string) {
  if (servings === 1) return serving
  return `${servingsText(servings)} ${servings < 1 ? "serving" : "servings"} (${serving})`
}

export function MealList({ meals, entries, foods, fresh, dense = false, onEdit, onAdd }: Props) {
  const names = [...meals, ...new Set(entries.map((e) => e.meal).filter((m) => !meals.includes(m)))]
  return (
    <div className={cn("flex flex-col", dense ? "gap-3" : "gap-5")}>
      {names.map((meal) => {
        const list = entries.filter((e) => e.meal === meal && foods.has(e.foodId)).toSorted((a, b) => a.at - b.at)
        const kcal = totals(list, foods).calories
        return (
          <section key={meal} aria-labelledby={`meal-${meal}`} className="flex flex-col gap-1">
            <header className="flex items-center gap-2">
              <h3 id={`meal-${meal}`} className="text-sm font-semibold">
                {meal}
              </h3>
              <span className="text-sm text-muted-foreground tabular-nums">{list.length ? `${fmt(kcal)} kcal` : ""}</span>
              <Button variant="ghost" size="icon" className={cn("ml-auto rounded-full text-muted-foreground", dense ? "size-8" : "size-10")} aria-label={`Add to ${meal}`} onClick={() => onAdd(meal)}>
                <Plus />
              </Button>
            </header>
            {list.length === 0 ? (
              !dense && <p className="pb-1 text-sm text-muted-foreground">Nothing logged yet.</p>
            ) : (
              <ul className="flex flex-col">
                {list.map((e) => {
                  const f = foods.get(e.foodId)!
                  return (
                    <li key={e.id} className={cn(fresh.has(e.id) && "entry-in")}>
                      <button
                        type="button"
                        onClick={() => onEdit(e, f)}
                        className={cn(
                          "-mx-2 flex w-[calc(100%+1rem)] items-center gap-3 rounded-lg px-2 text-left outline-none transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50",
                          dense ? "py-1" : "py-2",
                        )}
                      >
                        <FoodDisc food={f} className={dense ? "size-8 text-sm" : "size-9 text-base"} />
                        <span className={cn("flex min-w-0 flex-1", dense ? "items-baseline gap-2" : "flex-col")}>
                          <span className="truncate text-base">{f.name}</span>
                          <span className="truncate text-sm text-muted-foreground">{portion(e.servings, f.serving)}</span>
                        </span>
                        <span className="text-base tabular-nums">{fmt(f.calories * e.servings)}</span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        )
      })}
    </div>
  )
}
