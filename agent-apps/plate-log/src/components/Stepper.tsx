import { Minus, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { servingsText } from "@/lib/nutrition"

/** Servings in quarter steps, from a quarter to twenty. */
export function Stepper({ value, onChange, label }: { value: number; onChange: (n: number) => void; label: string }) {
  const set = (n: number) => onChange(Math.min(20, Math.max(0.25, Math.round(n * 4) / 4)))
  return (
    <div role="group" aria-label={label} className="flex items-center gap-3">
      <Button variant="outline" size="icon" className="size-11 rounded-full" aria-label="A quarter less" onClick={() => set(value - 0.25)} disabled={value <= 0.25}>
        <Minus />
      </Button>
      <output aria-live="polite" className="min-w-16 text-center text-title font-semibold tabular-nums">
        {servingsText(value)}
      </output>
      <Button variant="outline" size="icon" className="size-11 rounded-full" aria-label="A quarter more" onClick={() => set(value + 0.25)} disabled={value >= 20}>
        <Plus />
      </Button>
    </div>
  )
}
