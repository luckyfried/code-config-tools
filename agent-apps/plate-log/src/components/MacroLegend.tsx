import type { Macros } from "@/lib/config"
import { fmt } from "@/lib/nutrition"
import { cn } from "@/lib/utils"

const ROWS = [
  { key: "protein", label: "Protein", dot: "border-protein" },
  { key: "carbs", label: "Carbs", dot: "border-carbs" },
  { key: "fat", label: "Fat", dot: "border-fat" },
] as const

export function MacroLegend({ eaten, targets, className }: { eaten: Macros; targets: Macros; className?: string }) {
  return (
    <dl className={cn("grid grid-cols-3 gap-3", className)}>
      {ROWS.map((r) => {
        /* Rounded once, so eaten and to-go (or over) add up to the target shown. */
        const ate = Math.round(eaten[r.key])
        const target = Math.round(targets[r.key])
        const left = target - ate
        return (
          <div key={r.key} className="flex flex-col">
            <dt className="flex items-center gap-2 text-sm text-muted-foreground">
              <span aria-hidden="true" className={cn("size-3 rounded-full border-[3px]", r.dot)} />
              {r.label}
            </dt>
            <dd className="flex flex-col pl-5">
              <span className="text-lg font-semibold whitespace-nowrap tabular-nums">
                {fmt(ate)}
                <span className="text-sm font-normal text-muted-foreground"> / {fmt(target)} g</span>
              </span>
              <span className={cn("text-xs tabular-nums", left < 0 ? "text-destructive" : "text-muted-foreground")}>
                {left < 0 ? `${fmt(-left)} g over` : `${fmt(left)} g to go`}
              </span>
            </dd>
          </div>
        )
      })}
    </dl>
  )
}
