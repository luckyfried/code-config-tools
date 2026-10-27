import { MinusIcon, PlusIcon } from "lucide-react"
import { useId } from "react"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import type { Recipe } from "@/lib/config"
import { servingsFor, servingsStore, useStore } from "@/lib/store"
import { cn } from "@/lib/utils"

export function useServings(recipe: Recipe) {
  const chosen = useStore(servingsStore)
  const servings = servingsFor(recipe.id, recipe.servings, chosen)
  const set = (value: number) => servingsStore.set((current) => ({ ...current, [recipe.id]: value }))
  return { servings, factor: servings / recipe.servings, set }
}

/** The servings slider: every quantity on the page follows it live. */
export function ServingsControl({ recipe, className }: { recipe: Recipe; className?: string }) {
  const { servings, set } = useServings(recipe)
  const max = Math.max(12, recipe.servings * 3)
  const label = useId()
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-baseline justify-between gap-3">
        <p id={label} className="text-sm text-muted-foreground">
          Cooking for <span className="font-semibold text-foreground nums">{servings}</span>
          {servings !== recipe.servings ? <span className="nums"> (written for {recipe.servings})</span> : null}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="icon" aria-label="One fewer serving" disabled={servings <= 1} onClick={() => set(servings - 1)}>
          <MinusIcon />
        </Button>
        <Slider
          aria-labelledby={label}
          min={1}
          max={max}
          step={1}
          value={[servings]}
          onValueChange={([value]) => set(value)}
          className="mx-1 flex-1 py-3 **:data-[slot=slider-thumb]:size-6 **:data-[slot=slider-thumb]:border-2 **:data-[slot=slider-thumb]:border-primary **:data-[slot=slider-thumb]:bg-stage **:data-[slot=slider-track]:h-1.5"
        />
        <Button variant="outline" size="icon" aria-label="One more serving" disabled={servings >= max} onClick={() => set(servings + 1)}>
          <PlusIcon />
        </Button>
      </div>
    </div>
  )
}
