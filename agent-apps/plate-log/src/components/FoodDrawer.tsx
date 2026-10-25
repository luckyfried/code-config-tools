import { useState } from "react"
import { Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from "@/components/ui/drawer"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { FoodDisc } from "./FoodDisc"
import { Stepper } from "./Stepper"
import { useMedia } from "@/hooks/useMedia"
import type { Food } from "@/lib/config"
import { fmt } from "@/lib/nutrition"

export type DrawerState =
  | { mode: "add"; food: Food; servings: number; meal: string }
  | { mode: "edit"; food: Food; servings: number; meal: string; entryId: string }

type Props = {
  state: DrawerState | null
  meals: string[]
  onClose: () => void
  onConfirm: (servings: number, meal: string) => void
  onRemove: () => void
}

export function FoodDrawer({ state, meals, onClose, onConfirm, onRemove }: Props) {
  const wide = useMedia("(min-width: 1024px)")
  return (
    <Drawer open={state !== null} onOpenChange={(open) => !open && onClose()} direction={wide ? "right" : "bottom"}>
      <DrawerContent className="data-[vaul-drawer-direction=right]:sm:max-w-md">
        {state && <Body key={state.mode === "edit" ? state.entryId : state.food.id} state={state} meals={meals} onConfirm={onConfirm} onRemove={onRemove} />}
      </DrawerContent>
    </Drawer>
  )
}

function Body({ state, meals, onConfirm, onRemove }: Omit<Props, "onClose" | "state"> & { state: DrawerState }) {
  const [servings, setServings] = useState(state.servings)
  const [meal, setMeal] = useState(state.meal)
  const f = state.food
  const n = (v: number) => fmt(v * servings)

  return (
    <div className="mx-auto flex w-full max-w-md flex-col">
      <DrawerHeader className="flex-row items-center gap-3 text-left md:gap-3">
        <FoodDisc food={f} className="size-12" />
        <div className="flex min-w-0 flex-col gap-0.5 text-left">
          <DrawerTitle className="truncate text-lg font-semibold">{f.name}</DrawerTitle>
          <DrawerDescription>One serving is {f.serving}.</DrawerDescription>
        </div>
      </DrawerHeader>

      <div className="flex min-w-0 flex-col items-center gap-5 px-4 pb-2">
        <Stepper value={servings} onChange={setServings} label="Servings" />
        <dl className="grid w-full grid-cols-4 gap-2 text-center">
          <Stat label="kcal" value={n(f.calories)} dot="bg-energy" />
          <Stat label="protein" value={`${n(f.protein)} g`} dot="bg-protein" />
          <Stat label="carbs" value={`${n(f.carbs)} g`} dot="bg-carbs" />
          <Stat label="fat" value={`${n(f.fat)} g`} dot="bg-fat" />
        </dl>
        <ToggleGroup
          type="single"
          value={meal}
          onValueChange={(v) => v && setMeal(v)}
          variant="outline"
          className="grid w-full grid-cols-2 sm:grid-cols-4"
          aria-label="Meal"
        >
          {meals.map((m) => (
            <ToggleGroupItem key={m} value={m} className="h-11 w-full min-w-0 px-2 text-sm data-[state=on]:border-primary data-[state=on]:bg-primary/10 data-[state=on]:text-foreground">
              {m}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </div>

      <DrawerFooter className="pb-[max(1rem,env(safe-area-inset-bottom))]">
        <Button className="h-12 text-base" onClick={() => onConfirm(servings, meal)}>
          {state.mode === "add" ? `Add to ${meal}` : "Save"}
        </Button>
        {state.mode === "edit" && (
          <Button variant="ghost" className="h-11 text-destructive" onClick={onRemove}>
            <Trash2 data-icon="inline-start" />
            Remove from {state.meal}
          </Button>
        )}
      </DrawerFooter>
    </div>
  )
}

function Stat({ label, value, dot }: { label: string; value: string; dot: string }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-lg bg-muted px-1 py-2">
      <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span aria-hidden="true" className={`size-2 rounded-full ${dot}`} />
        {label}
      </dt>
      <dd className="text-sm font-semibold tabular-nums">{value}</dd>
    </div>
  )
}
