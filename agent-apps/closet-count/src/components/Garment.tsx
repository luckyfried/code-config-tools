import type { CSSProperties } from "react"
import { cn } from "@/lib/utils"
import { toneOf } from "@/lib/color"
import type { Category } from "@/lib/types"

/** One silhouette from garments.svg, tinted with the item's color and faded by its dust. */
export function Garment({
  category,
  color,
  dust = 0,
  className,
}: {
  category: Category
  color: string
  dust?: number
  className?: string
}) {
  return (
    <svg
      viewBox="0 0 100 100"
      aria-hidden="true"
      data-tone={toneOf(color)}
      className={cn("garment block", className)}
      style={{ "--tint": color, "--dust": dust } as CSSProperties}
    >
      <use href={`./garments.svg#${category}`} />
    </svg>
  )
}
