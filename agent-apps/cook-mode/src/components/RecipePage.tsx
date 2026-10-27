import { ArrowLeftIcon, ArrowRightIcon, BookmarkCheckIcon, BookmarkPlusIcon } from "lucide-react"
import { useId, type CSSProperties } from "react"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { config, type Recipe } from "@/lib/config"
import { cuisineTint } from "@/lib/cuisine"
import { useFlip } from "@/lib/flip"
import { shownIngredient } from "@/lib/quantity"
import { go, href } from "@/lib/router"
import { haveStore, toggleIn, useStore, weekStore } from "@/lib/store"
import { AppHeader } from "./AppHeader"
import { ServingsControl, useServings } from "./ServingsControl"
import { StepText } from "./StepText"
import { TimeArc } from "./TimeArc"

function IngredientRow({ recipe, index, factor }: { recipe: Recipe; index: number; factor: number }) {
  const have = useStore(haveStore)
  const id = useId()
  const key = `${recipe.id}:${index}`
  const ingredient = recipe.ingredients[index]
  const shown = shownIngredient(ingredient, factor, config.units)
  const onList = !have.includes(key)
  return (
    <li data-flip={key} className="flex items-start gap-3 py-2">
      <Checkbox
        id={id}
        checked={onList}
        onCheckedChange={() => haveStore.set((list) => toggleIn(list, key))}
        className="mt-0.5 size-5"
      />
      <label htmlFor={id} className="flex-1 cursor-pointer text-[16px] leading-snug">
        {shown.amount !== "" ? (
          <span className="mr-1.5 font-semibold nums">
            {shown.amount}
            {shown.unit ? ` ${shown.unit}` : ""}
          </span>
        ) : null}
        <span className={onList ? "" : "text-muted-foreground"}>{shown.name}</span>
      </label>
    </li>
  )
}

export function RecipePage({ recipe }: { recipe: Recipe }) {
  const { factor, servings } = useServings(recipe)
  const week = useStore(weekStore)
  const marked = week.includes(recipe.id)
  const list = useFlip<HTMLUListElement>(servings)
  const cook = () => go({ name: "cook", id: recipe.id, step: 1 })

  return (
    <>
      <AppHeader current="recipe" />
      <main className="gutter safe-x safe-bottom pb-24" style={{ "--tint": cuisineTint(recipe.cuisine) } as CSSProperties}>
        <a href={href({ name: "index" })} className="-ml-1 inline-flex h-10 items-center gap-1.5 rounded-lg px-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeftIcon className="size-4" aria-hidden="true" />
          All recipes
        </a>
        <header className="mt-2 flex flex-col gap-5 border-b border-border pb-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex max-w-4xl flex-col gap-4">
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <span className="tint-edge h-4 w-1.5 rounded-full" aria-hidden="true" />
              {recipe.cuisine}
              {recipe.tags.length ? <span aria-hidden="true">/</span> : null}
              {recipe.tags.join(", ")}
            </p>
            <h1 className="title-type text-[34px] leading-[1.06] font-semibold sm:text-5xl xl:text-6xl">{recipe.title}</h1>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
              <TimeArc minutes={recipe.minutes} className="text-foreground" />
              <span className="nums">{recipe.ingredients.length} ingredients</span>
              <span className="nums">{recipe.steps.length} steps</span>
            </div>
          </div>
          <div className="flex gap-2">
            <Button size="lg" className="flex-1 lg:flex-none" onClick={cook}>
              Cook
              <ArrowRightIcon data-icon="inline-end" />
            </Button>
            <Button size="lg" variant="outline" aria-pressed={marked} onClick={() => weekStore.set((ids) => toggleIn(ids, recipe.id))}>
              {marked ? <BookmarkCheckIcon data-icon="inline-start" className="text-primary" /> : <BookmarkPlusIcon data-icon="inline-start" />}
              {marked ? "On this week" : "Cook this week"}
            </Button>
          </div>
        </header>

        {recipe.image ? (
          <img
            src={recipe.image}
            alt=""
            width={1600}
            height={900}
            className="mt-8 aspect-[16/7] w-full rounded-3xl object-cover outline outline-1 -outline-offset-1 outline-black/10"
          />
        ) : null}

        <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(300px,4fr)_8fr] lg:gap-14">
          <aside className="flex flex-col gap-5 lg:sticky lg:top-6 lg:self-start" aria-labelledby="ingredients">
            <div className="flex items-baseline justify-between">
              <h2 id="ingredients" className="title-type text-2xl font-semibold">
                Ingredients
              </h2>
            </div>
            <ServingsControl recipe={recipe} />
            <ul ref={list} className="flex flex-col divide-y divide-border/70">
              {recipe.ingredients.map((_, index) => (
                <IngredientRow key={index} recipe={recipe} index={index} factor={factor} />
              ))}
            </ul>
            <p className="text-sm text-muted-foreground">Ticked items go on the shopping list when this recipe is on this week.</p>
          </aside>

          <section aria-labelledby="method">
            <h2 id="method" className="title-type text-2xl font-semibold">
              Method
            </h2>
            <ol className="mt-4 flex flex-col">
              {recipe.steps.map((_, index) => (
                <li key={index} className="grid grid-cols-[2.5rem_1fr] gap-x-3 border-b border-border/70 py-6 last:border-0 sm:grid-cols-[3.5rem_1fr]">
                  <span className="title-type text-3xl leading-none font-semibold text-primary nums sm:text-4xl" aria-hidden="true">
                    {index + 1}
                  </span>
                  <p className="font-serif text-[19px] leading-relaxed sm:text-[21px]">
                    <span className="sr-only">Step {index + 1}. </span>
                    <StepText recipe={recipe} stepIndex={index} />
                  </p>
                </li>
              ))}
            </ol>
            <Button size="lg" className="mt-4 w-full sm:w-auto" onClick={cook}>
              Cook this, one step at a time
              <ArrowRightIcon data-icon="inline-end" />
            </Button>
          </section>
        </div>
      </main>
    </>
  )
}
