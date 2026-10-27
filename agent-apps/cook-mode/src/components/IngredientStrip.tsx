import { cn } from "@/lib/utils"
import { config, ingredientsForStep, type Recipe } from "@/lib/config"
import { useFlip } from "@/lib/flip"
import { shownIngredient } from "@/lib/quantity"

interface IngredientStripProps {
  recipe: Recipe
  stepIndex: number
  factor: number
  className?: string
}

/** The ingredients this step needs, scaled, in a row that re-flows smoothly when they change. */
export function IngredientStrip({ recipe, stepIndex, factor, className }: IngredientStripProps) {
  const items = ingredientsForStep(recipe, stepIndex)
  const ref = useFlip<HTMLUListElement>(`${stepIndex}:${factor}`)
  return (
    <div className={cn("rounded-2xl border border-stage-edge bg-strip p-2 short:p-1.5", className)}>
      {items.length === 0 ? (
        <p className="px-2 py-1.5 text-sm text-muted-foreground">Nothing new goes in on this step.</p>
      ) : (
        <ul ref={ref} className="flex flex-wrap gap-1.5" aria-label="Ingredients for this step">
          {items.map(({ ingredient, index }) => {
            const shown = shownIngredient(ingredient, factor, config.units)
            return (
              <li
                key={index}
                data-flip={`${recipe.id}:${index}`}
                className="flex min-h-10 items-baseline gap-1.5 rounded-xl bg-stage px-3 py-2 text-[15px] leading-tight shadow-card short:min-h-0 short:rounded-lg short:px-2.5 short:py-1.5 short:text-[13px]"
              >
                {shown.amount !== "" ? (
                  <span className="font-semibold nums text-stage-foreground">
                    {shown.amount}
                    {shown.unit ? <span className="font-medium">{` ${shown.unit}`}</span> : null}
                  </span>
                ) : null}
                <span className="text-stage-foreground/80">{shown.name}</span>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
