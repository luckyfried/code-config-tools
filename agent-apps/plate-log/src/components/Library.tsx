import { useState } from "react"
import { Check, Plus } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import type { Food, Usual } from "@/lib/config"
import { fmt } from "@/lib/nutrition"
import { FoodDisc } from "./FoodDisc"

type Props = {
  foods: Food[]
  onPick: (f: Food) => void
  onSave: (f: Food) => void
  takenIds: Set<string>
  /** Beside the tiles, the list stays closed until a search is typed, so it never repeats them. */
  searchOnly?: boolean
}

export function Library({ foods, onPick, onSave, takenIds, searchOnly = false }: Props) {
  const [adding, setAdding] = useState(false)
  const [savedName, setSavedName] = useState("")
  const [query, setQuery] = useState("")
  const open = !searchOnly || query.trim() !== ""

  return (
    <div className="flex flex-col gap-4">
      <Command className="rounded-xl border bg-card p-1" loop>
        <CommandInput id="library-search" placeholder={searchOnly ? `Search all ${foods.length} foods` : "Search your foods"} className="text-base" value={query} onValueChange={setQuery} />
        <CommandList className={open ? "max-h-none lg:max-h-[22rem]" : "hidden"}>
          <CommandEmpty>No food by that name. Add it below.</CommandEmpty>
          <CommandGroup heading={searchOnly ? undefined : `${foods.length} foods`}>
            {foods.map((f) => (
              <CommandItem key={f.id} value={`${f.name} ${f.id}`} onSelect={() => {
                  onPick(f)
                  if (searchOnly) setQuery("")
                }} className="gap-3 py-2">
                <FoodDisc food={f} className="size-8 text-sm" />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-sm font-medium">{f.name}</span>
                  <span className="truncate text-xs text-muted-foreground">{f.serving}</span>
                </span>
                <span className="text-sm text-muted-foreground tabular-nums">{fmt(f.calories)} kcal</span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>

      {savedName && !adding && (
        <p role="status" className="flex items-center gap-2 text-sm text-muted-foreground">
          <Check className="size-4 text-fat-deep dark:text-fat" aria-hidden="true" />
          {savedName} is in your foods.
        </p>
      )}

      {adding ? (
        <NewFood
          takenIds={takenIds}
          onCancel={() => setAdding(false)}
          onSave={(f) => {
            onSave(f)
            setSavedName(f.name)
            setAdding(false)
          }}
        />
      ) : (
        <Button variant="outline" className="h-11 self-start" onClick={() => setAdding(true)}>
          <Plus data-icon="inline-start" />
          New food
        </Button>
      )}
    </div>
  )
}

const USUALS: { value: Usual; label: string }[] = [
  { value: "breakfast", label: "Breakfast" },
  { value: "lunch", label: "Lunch" },
  { value: "dinner", label: "Dinner" },
  { value: "snack", label: "Snack" },
]

function slug(name: string, taken: Set<string>) {
  const base = name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "food"
  let id = base
  for (let n = 2; taken.has(id); n++) id = `${base}-${n}`
  return id
}

function NewFood({ onSave, onCancel, takenIds }: { onSave: (f: Food) => void; onCancel: () => void; takenIds: Set<string> }) {
  const [name, setName] = useState("")
  const [serving, setServing] = useState("")
  const [nums, setNums] = useState({ calories: "", protein: "", carbs: "", fat: "" })
  const [usual, setUsual] = useState<Usual | "">("")
  const [tried, setTried] = useState(false)

  const num = (s: string) => (s.trim() === "" ? NaN : Number(s.replace(",", ".")))
  const bad = {
    name: !name.trim(),
    calories: !(num(nums.calories) >= 0),
    protein: !(num(nums.protein) >= 0),
    carbs: !(num(nums.carbs) >= 0),
    fat: !(num(nums.fat) >= 0),
  }
  const ok = !Object.values(bad).some(Boolean)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setTried(true)
    if (!ok) return
    onSave({
      id: slug(name, takenIds),
      name: name.trim(),
      serving: serving.trim() || "1 serving",
      calories: num(nums.calories),
      protein: num(nums.protein),
      carbs: num(nums.carbs),
      fat: num(nums.fat),
      ...(usual ? { usual } : {}),
    })
  }

  const numField = (key: keyof typeof nums, label: string, unit: string) => (
    <Field data-invalid={tried && bad[key] ? true : undefined}>
      <FieldLabel htmlFor={`nf-${key}`}>
        {label} <span className="font-normal text-muted-foreground">{unit}</span>
      </FieldLabel>
      <Input
        id={`nf-${key}`}
        inputMode="decimal"
        autoComplete="off"
        className="h-11 text-base tabular-nums"
        value={nums[key]}
        aria-invalid={tried && bad[key] ? true : undefined}
        onChange={(e) => setNums({ ...nums, [key]: e.target.value })}
      />
    </Field>
  )

  return (
    <form onSubmit={submit} className="flex flex-col gap-4 rounded-xl border bg-card p-4" aria-labelledby="new-food">
      <h3 id="new-food" className="text-lg font-semibold">
        New food
      </h3>
      <FieldGroup className="gap-4">
        <Field data-invalid={tried && bad.name ? true : undefined}>
          <FieldLabel htmlFor="nf-name">Name</FieldLabel>
          <Input id="nf-name" autoComplete="off" className="h-11 text-base" value={name} aria-invalid={tried && bad.name ? true : undefined} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field>
          <FieldLabel htmlFor="nf-serving">One serving</FieldLabel>
          <Input id="nf-serving" autoComplete="off" placeholder="1 bowl" className="h-11 text-base" value={serving} onChange={(e) => setServing(e.target.value)} />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          {numField("calories", "Calories", "kcal")}
          {numField("protein", "Protein", "g")}
          {numField("carbs", "Carbs", "g")}
          {numField("fat", "Fat", "g")}
        </div>
        <Field>
          <FieldLabel>Usually eaten at</FieldLabel>
          <ToggleGroup type="single" variant="outline" value={usual} onValueChange={(v) => setUsual(v as Usual | "")} className="flex-wrap justify-start">
            {USUALS.map((u) => (
              <ToggleGroupItem key={u.value} value={u.value} className="h-11 px-3 text-sm">
                {u.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </Field>
      </FieldGroup>
      {tried && !ok && <p className="text-sm text-destructive">Give the food a name and a number for calories, protein, carbs, and fat.</p>}
      <div className="flex gap-2">
        <Button type="submit" className="h-11 flex-1">
          Save food
        </Button>
        <Button type="button" variant="ghost" className="h-11" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </form>
  )
}
