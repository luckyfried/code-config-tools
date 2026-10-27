import { ArrowRightIcon, XIcon } from "lucide-react"
import { useId, type CSSProperties } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { config, recipeById, type Recipe } from "@/lib/config"
import { cuisineTint } from "@/lib/cuisine"
import { nameFor, showQuantity } from "@/lib/quantity"
import { href } from "@/lib/router"
import { gotStore, haveStore, servingsFor, servingsStore, toggleIn, useStore, weekStore } from "@/lib/store"
import { AppHeader } from "./AppHeader"
import { TimeArc } from "./TimeArc"

interface Line {
  key: string
  amount: string
  unit: string
  name: string
  from: string[]
}

interface Part {
  recipe: Recipe
  lines: Line[]
}

function baseName(name: string) {
  return name.split(",")[0].trim()
}

function build(week: Recipe[], chosen: Record<string, number>, have: string[]) {
  const merged = new Map<string, { name: string; unit: string; total: number | null; from: Set<string> }>()
  const parts: Part[] = []
  for (const recipe of week) {
    const factor = servingsFor(recipe.id, recipe.servings, chosen) / recipe.servings
    const lines: Line[] = []
    recipe.ingredients.forEach((ingredient, index) => {
      if (have.includes(`${recipe.id}:${index}`) || /^(boiling |cold |hot |warm )?water$/i.test(baseName(ingredient.name))) return
      const shown = showQuantity(ingredient.amount, ingredient.unit, factor, config.units)
      const name = baseName(ingredient.name)
      const key = `${name.toLowerCase()}|${shown.key}`
      lines.push({ key: `${recipe.id}:${index}`, amount: shown.amount, unit: shown.unit, name: nameFor({ ...ingredient, name }, shown), from: [] })
      const entry = merged.get(key) ?? { name, unit: shown.key, total: null, from: new Set<string>() }
      if (shown.value !== null) entry.total = (entry.total ?? 0) + shown.value
      entry.from.add(recipe.title)
      merged.set(key, entry)
    })
    parts.push({ recipe, lines })
  }
  const all: Line[] = [...merged.entries()]
    .map(([key, entry]) => {
      const shown = entry.total === null ? null : showQuantity(entry.total, entry.unit, 1, config.units)
      return {
        key,
        amount: shown?.amount ?? "",
        unit: shown?.unit ?? "",
        name: shown ? nameFor({ amount: entry.total, unit: entry.unit, name: entry.name }, shown) : entry.name,
        from: [...entry.from],
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name))
  return { all, parts }
}

function LineRow({ line, showFrom }: { line: Line; showFrom: boolean }) {
  const got = useStore(gotStore)
  const id = useId()
  const done = got.includes(line.key)
  return (
    <li className="flex break-inside-avoid items-start gap-3 border-b border-border/70 py-3">
      <Checkbox id={id} checked={done} onCheckedChange={() => gotStore.set((list) => toggleIn(list, line.key))} className="mt-0.5 size-5" />
      <label htmlFor={id} className={done ? "flex-1 cursor-pointer text-muted-foreground line-through decoration-1" : "flex-1 cursor-pointer"}>
        <span className="block text-[16px] leading-snug">
          {line.amount ? (
            <span className="mr-1.5 font-semibold nums">
              {line.amount}
              {line.unit ? ` ${line.unit}` : ""}
            </span>
          ) : null}
          {line.name}
        </span>
        {showFrom && line.from.length ? <span className="mt-0.5 block text-sm text-muted-foreground">for {line.from.join(" and ")}</span> : null}
      </label>
    </li>
  )
}

export function ShoppingPage() {
  const ids = useStore(weekStore)
  const chosen = useStore(servingsStore)
  const have = useStore(haveStore)
  const got = useStore(gotStore)
  const week = ids.map((id) => recipeById.get(id)).filter((recipe): recipe is Recipe => Boolean(recipe))
  const { all, parts } = build(week, chosen, have)
  const left = all.filter((line) => !got.includes(line.key)).length

  return (
    <>
      <AppHeader current="shopping" />
      <main className="gutter safe-x safe-bottom pb-24">
        <div className="flex flex-col gap-2 border-b border-border pb-6 pt-2">
          <h1 className="title-type text-4xl font-semibold sm:text-5xl">Shopping</h1>
          <p className="text-muted-foreground nums">
            {week.length === 0
              ? "Nothing is on this week yet."
              : `${left} of ${all.length} things still to get, for ${week.length} ${week.length === 1 ? "recipe" : "recipes"} this week.`}
          </p>
        </div>

        {week.length === 0 ? (
          <div className="flex flex-col items-start gap-4 py-12">
            <p className="max-w-prose text-lg">Mark a recipe for this week from its card or its page, and everything it needs lands here as one list.</p>
            <Button size="lg" asChild>
              <a href={href({ name: "index" })}>
                Choose recipes
                <ArrowRightIcon data-icon="inline-end" />
              </a>
            </Button>
          </div>
        ) : (
          <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(280px,1fr)_3fr] lg:gap-14">
            <section aria-labelledby="this-week" className="flex flex-col gap-3">
              <h2 id="this-week" className="title-type text-2xl font-semibold">
                This week
              </h2>
              <ul className="flex flex-col gap-2">
                {week.map((recipe) => (
                  <li
                    key={recipe.id}
                    className="relative flex items-center gap-3 overflow-hidden rounded-xl bg-card py-3 pr-2 pl-5 shadow-card"
                    style={{ "--tint": cuisineTint(recipe.cuisine) } as CSSProperties}
                  >
                    <span className="tint-edge absolute inset-y-0 left-0 w-1.5" aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                      <a href={href({ name: "recipe", id: recipe.id })} className="title-type block truncate text-lg font-semibold hover:underline">
                        {recipe.title}
                      </a>
                      <p className="flex items-center gap-3 text-sm text-muted-foreground nums">
                        <span>Cooking for {servingsFor(recipe.id, recipe.servings, chosen)}</span>
                        <TimeArc minutes={recipe.minutes} label={false} className="[&_svg]:size-5" />
                      </p>
                    </div>
                    <Button variant="ghost" size="icon" aria-label={`Take ${recipe.title} off this week`} onClick={() => weekStore.set((list) => toggleIn(list, recipe.id))}>
                      <XIcon />
                    </Button>
                  </li>
                ))}
              </ul>
              <Button variant="outline" asChild className="self-start">
                <a href={href({ name: "index" })}>Add another recipe</a>
              </Button>
            </section>

            <section aria-label="The list">
              <Tabs defaultValue="one">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <TabsList>
                    <TabsTrigger value="one">One list</TabsTrigger>
                    <TabsTrigger value="recipe">By recipe</TabsTrigger>
                  </TabsList>
                  {got.length ? (
                    <Button variant="ghost" onClick={() => gotStore.set([])}>
                      Untick everything
                    </Button>
                  ) : null}
                </div>
                <TabsContent value="one" className="mt-4">
                  {all.length ? (
                    <ul className="gap-x-10 md:columns-2">
                      {all.map((line) => (
                        <LineRow key={line.key} line={line} showFrom={week.length > 1} />
                      ))}
                    </ul>
                  ) : (
                    <p className="py-6 text-muted-foreground">Everything is already in the kitchen. Untick an ingredient on a recipe to put it on the list.</p>
                  )}
                </TabsContent>
                <TabsContent value="recipe" className="mt-4 flex flex-col gap-8">
                  {parts.map((part) => (
                    <div key={part.recipe.id}>
                      <h3 className="title-type text-xl font-semibold">{part.recipe.title}</h3>
                      <ul className="mt-2 gap-x-10 md:columns-2">
                        {part.lines.map((line) => (
                          <LineRow key={line.key} line={line} showFrom={false} />
                        ))}
                      </ul>
                    </div>
                  ))}
                </TabsContent>
              </Tabs>
            </section>
          </div>
        )}
      </main>
    </>
  )
}
