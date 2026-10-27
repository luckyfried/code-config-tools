import { useMemo, useState } from "react"
import { config } from "@/lib/config"
import { cn } from "@/lib/utils"
import { AppHeader } from "./AppHeader"
import { RecipeCard } from "./RecipeCard"
import { TonightHero, pinnedRecipe } from "./TonightHero"

export function IndexPage() {
  const [tag, setTag] = useState<string | null>(null)
  const tonight = pinnedRecipe()
  const tags = useMemo(() => {
    const used = new Set(config.recipes.flatMap((recipe) => recipe.tags))
    const ordered = config.tags.filter((name) => used.has(name))
    return [...ordered, ...[...used].filter((name) => !ordered.includes(name)).sort()]
  }, [])
  const shown = tag ? config.recipes.filter((recipe) => recipe.tags.includes(tag)) : config.recipes

  if (!tonight) {
    return (
      <>
        <AppHeader current="index" />
        <main className="gutter safe-x py-16">
          <h1 className="title-type text-3xl font-semibold">No recipes yet</h1>
          <p className="mt-3 max-w-prose text-muted-foreground">
            Send a recipe as a link, a photo of a card, or a few lines describing it, and it will be written up here.
          </p>
        </main>
      </>
    )
  }

  return (
    <>
      <AppHeader current="index" />
      <main>
        <TonightHero recipe={tonight} />
        <section aria-labelledby="all-recipes" className="gutter safe-x safe-bottom pb-16">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <h2 id="all-recipes" className="title-type text-2xl font-semibold sm:text-3xl">
              All recipes <span className="font-sans text-base font-normal text-muted-foreground nums">{config.recipes.length}</span>
            </h2>
          </div>
          <div className="no-scrollbar -mx-4 mt-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:px-0" role="group" aria-label="Filter by tag">
            {[null, ...tags].map((name) => (
              <button
                key={name ?? "all"}
                type="button"
                onClick={() => setTag(name)}
                aria-pressed={tag === name}
                className={cn(
                  "h-10 shrink-0 cursor-pointer rounded-full border px-4 text-sm font-medium transition-[color,background-color,border-color] duration-150",
                  tag === name
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border bg-card/60 text-muted-foreground hover:border-foreground/30 hover:text-foreground",
                )}
              >
                {name ?? "All"}
              </button>
            ))}
          </div>
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {shown.map((recipe) => (
              <RecipeCard key={recipe.id} recipe={recipe} tonight={recipe.id === tonight.id} />
            ))}
          </div>
        </section>
      </main>
    </>
  )
}
