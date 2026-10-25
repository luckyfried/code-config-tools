import { cn } from "@/lib/utils"
import type { Food } from "@/lib/config"
import { leadMacro } from "@/lib/nutrition"

const TINT = {
  protein: "bg-protein/15 text-protein-deep dark:bg-protein/20 dark:text-protein",
  carbs: "bg-carbs/20 text-carbs-deep dark:bg-carbs/20 dark:text-carbs",
  fat: "bg-fat/15 text-fat-deep dark:bg-fat/20 dark:text-fat",
}

/** The food's initial on a disc tinted by the macro that brings it the most calories. */
export function FoodDisc({ food, className }: { food: Food; className?: string }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex size-10 shrink-0 items-center justify-center rounded-full text-lg font-semibold",
        TINT[leadMacro(food)],
        className,
      )}
    >
      {food.name.trim().charAt(0).toUpperCase()}
    </span>
  )
}
