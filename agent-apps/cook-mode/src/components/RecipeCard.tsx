import { BookmarkCheckIcon, BookmarkPlusIcon } from "lucide-react"
import type { CSSProperties } from "react"
import type { Recipe } from "@/lib/config"
import { cuisineTint } from "@/lib/cuisine"
import { href } from "@/lib/router"
import { toggleIn, useStore, weekStore } from "@/lib/store"
import { cn } from "@/lib/utils"
import { TimeArc } from "./TimeArc"

function keyIngredients(recipe: Recipe) {
  return recipe.ingredients
    .filter((item) => item.amount !== null && !/oil|salt|water|sugar|pepper/i.test(item.name))
    .slice(0, 4)
    .map((item) => item.name.split(",")[0].replace(/\s*\(.*\)/, ""))
    .join(", ")
}

export function RecipeCard({ recipe, tonight }: { recipe: Recipe; tonight: boolean }) {
  const week = useStore(weekStore)
  const marked = week.includes(recipe.id)
  return (
    <article
      className="group relative flex min-h-56 flex-col overflow-hidden rounded-2xl bg-card text-card-foreground shadow-card transition-transform duration-200 ease-out has-[a:focus-visible]:outline-2 has-[a:focus-visible]:outline-offset-2 has-[a:focus-visible]:outline-ring"
      style={{ "--tint": cuisineTint(recipe.cuisine) } as CSSProperties}
    >
      <span className="tint-edge absolute inset-y-0 left-0 w-1.5" aria-hidden="true" />
      <div className="flex flex-1 flex-col gap-3 py-5 pr-5 pl-6">
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">
            {recipe.cuisine}
            {tonight ? <span className="ml-2 rounded-full bg-primary px-2 py-0.5 text-xs font-semibold text-primary-foreground">Tonight</span> : null}
          </p>
          <TimeArc minutes={recipe.minutes} className="text-muted-foreground" />
        </div>
        <h3 className="title-type text-[22px] leading-tight font-semibold">
          <a href={href({ name: "recipe", id: recipe.id })} className="outline-none after:absolute after:inset-0 after:content-['']">
            {recipe.title}
          </a>
        </h3>
        <p className="line-clamp-2 text-sm text-muted-foreground first-letter:uppercase">{keyIngredients(recipe)}</p>
        <div className="mt-auto flex items-end justify-between gap-3 pt-1">
          <ul className="flex flex-wrap gap-1.5" aria-label="Tags">
            {recipe.tags.map((tag) => (
              <li key={tag} className="rounded-full border border-border px-2.5 py-0.5 text-xs text-muted-foreground">
                {tag}
              </li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => weekStore.set((list) => toggleIn(list, recipe.id))}
            aria-pressed={marked}
            aria-label={marked ? `Take ${recipe.title} off this week` : `Cook ${recipe.title} this week`}
            className={cn(
              "relative z-10 -mr-2 -mb-2 flex size-11 shrink-0 cursor-pointer items-center justify-center rounded-full transition-[color,background-color,transform] duration-150 ease-out active:scale-95",
              marked ? "text-primary" : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {marked ? <BookmarkCheckIcon className="size-5" /> : <BookmarkPlusIcon className="size-5" />}
          </button>
        </div>
      </div>
    </article>
  )
}
